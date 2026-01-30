# Google Cloud Logging SecOps Data Ingest calculation script on ORG and project(s)
# and includes Logging Sinks. Period is 30 days time frame. 
# Jorge Liauw Calo - 2026
#
# ==============================================================================
# DISCLAIMER
# ==============================================================================
# This script is provided for informational purposes only and is not an official 
# Google tool. It is intended to help estimate log ingestion volumes based on 
# Cloud Monitoring metrics for Google SecOps. Please contact your Sales or CE for usage.
#
# BY RUNNING THIS SCRIPT, YOU ACKNOWLEDGE AND AGREE THAT:
# 1. YOU USE THIS SCRIPT AT YOUR OWN RISK.
# 2. THE AUTHOR(S) AND DISTRIBUTORS ARE NOT LIABLE FOR ANY ERRORS, OMISSIONS, 
#    OR DAMAGES (DIRECT, INDIRECT, OR CONSEQUENTIAL) ARISING FROM ITS USE.
# 3. THIS SCRIPT DOES NOT CONSTITUTE OFFICIAL BILLING ADVICE. ALWAYS REFER TO 
#    YOUR OFFICIAL GOOGLE CLOUD INVOICE FOR EXACT CHARGES.
# ==============================================================================

import time
import argparse
import sys

# --- Imports ---
try:
    from google.cloud import monitoring_v3
    from google.cloud.monitoring_v3 import types
    from google.cloud import service_usage_v1
    from google.cloud import resourcemanager_v3
    from google.cloud import logging
except ImportError as e:
    print("CRITICAL ERROR: Missing required Google Cloud libraries.")
    print(f"Details: {e}")
    print("\nPlease run the following command to install them:")
    print("pip install google-cloud-logging google-cloud-monitoring google-cloud-service-usage google-cloud-resource-manager")
    sys.exit(1)

def get_projects_in_org(org_id):
    """
    Lists all ACTIVE projects within the Organization.
    """
    print(f"Searching for active projects in Org ID: {org_id}...")
    client = resourcemanager_v3.ProjectsClient()
    projects = []
    
    try:
        search_query = f"parent.type:organization parent.id:{org_id} state:ACTIVE"
        search_request = resourcemanager_v3.SearchProjectsRequest(query=search_query) 
        for project in client.search_projects(request=search_request):
            projects.append(project.project_id)
            
    except Exception as e:
        print(f"\n[!] Error listing projects: {e}")
        print("Tip: Ensure your account has 'Organization Viewer' or 'Folder Viewer' permissions.")
        sys.exit(1)

    print(f"Found {len(projects)} active projects.")
    return projects

def check_api_status(project_id):
    """
    Checks if Cloud Monitoring API is enabled.
    """
    client = service_usage_v1.ServiceUsageClient()
    service_name = f"projects/{project_id}/services/monitoring.googleapis.com"
    try:
        request = service_usage_v1.GetServiceRequest(name=service_name)
        response = client.get_service(request=request)
        return response.state == service_usage_v1.State.ENABLED
    except:
        return False

def get_volume(project_id, specific_log_filter=None):
    """
    Generic function to get bytes. 
    """
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"
    
    # --- Set to 30 days ---
    days = 30
    now = time.time()
    seconds = int(now)
    nanos = int((now - seconds) * 10**9)
    
    interval = types.TimeInterval({
        "end_time": {"seconds": seconds, "nanos": nanos},
        "start_time": {"seconds": (seconds - days * 24 * 60 * 60), "nanos": nanos},
    })

    metric_filter = 'metric.type = "logging.googleapis.com/byte_count"'
    if specific_log_filter:
        metric_filter += f' AND metric.label.log = "{specific_log_filter}"'

    aggregation = types.Aggregation({
        "alignment_period": {"seconds": days * 24 * 60 * 60}, 
        "per_series_aligner": types.Aggregation.Aligner.ALIGN_SUM,
        "cross_series_reducer": types.Aggregation.Reducer.REDUCE_SUM,
    })

    try:
        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": metric_filter,
                "interval": interval,
                "view": types.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation,
            }
        )
        total = 0
        for result in results:
            for point in result.points:
                total += point.value.int64_value
        return total
    except:
        return 0

def print_sink_details(project_id):
    """
    Fetches and prints Log Router Sinks for a project.
    """
    try:
        client = logging.Client(project=project_id)
        sinks = list(client.list_sinks())
        
        if not sinks:
            print(f"     [i] No Log Sinks configured.")
            return

        for sink in sinks:
            print(f"     > Sink Name:       {sink.name}")
            print(f"       Resource Name:   {sink.writer_identity}")
            print(f"       Destination:     {sink.destination}")
            
            inc_filter = sink.filter_ if sink.filter_ else "(All Logs)"
            if len(inc_filter) > 80: inc_filter = inc_filter[:77] + "..."
            print(f"       Inclusion Filt:  {inc_filter}")

            if sink.exclusions:
                print(f"       Exclusions:      {len(sink.exclusions)} found")
                for ex in sink.exclusions:
                    print(f"         - {ex.name}: {ex.filter_[:60]}...")
            else:
                print(f"       Exclusions:      None")
            print("")

    except Exception as e:
        print(f"     [!] Could not fetch sinks (Permission denied?): {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # --- PRINT DISCLAIMER ---
    print("\n" + "#" * 80)
    print(" DISCLAIMER - PLEASE READ CAREFULLY")
    print("#" * 80)
    print(" This script is provided for informational purposes only and is NOT an official")
    print(" Google product. It estimates log ingestion and lists sink configurations.")
    print("")
    print(" BY PROCEEDING, YOU ACKNOWLEDGE THAT:")
    print(" 1. YOU USE THIS SCRIPT AT YOUR OWN RISK.")
    print(" 2. THE AUTHOR(S) ARE NOT LIABLE FOR ANY ERRORS, OMISSIONS, OR DAMAGES.")
    print(" 3. THIS DOES NOT REPLACE YOUR OFFICIAL GOOGLE CLOUD INVOICE.")
    print("#" * 80 + "\n")

    try:
        agreement = input(">> Do you agree to these terms? (y/n): ").strip().lower()
    except KeyboardInterrupt:
        sys.exit(0)

    if agreement != 'y':
        print("\n[!] You did not agree to the terms. Exiting script.")
        sys.exit(0)

    print("\n" + "=" * 80)
    print("   Google Cloud Logging: Volume (30d) + Sink Logging Configs")
    print("=" * 80 + "\n")

    try:
        org_id = input(">> Please enter your Organization ID (e.g. 123456789): ").strip()
    except KeyboardInterrupt:
        sys.exit(0)

    if not org_id:
        print("[!] Error: You must enter an Organization ID.")
        sys.exit(1)

    print("-" * 80)
    projects = get_projects_in_org(org_id)
    
    if not projects:
        print("[!] No active projects found.")
        sys.exit(1)

    grand_total_bytes = 0
    grand_cai_bytes = 0
    
    # --- New Counters ---
    projects_scanned = 0
    projects_skipped = 0
    
    print("\nProcessing projects... (This may take a moment)\n")

    for pid in projects:
        print("-" * 80)
        print(f"PROJECT: {pid}")
        print("-" * 80)

        if check_api_status(pid):
            # Success Path
            projects_scanned += 1
            
            # 1. Get TOTAL Volume
            total_bytes = get_volume(pid)
            cai_bytes = get_volume(pid, specific_log_filter="cloudasset.googleapis.com/temporal_asset")
            
            grand_total_bytes += total_bytes
            grand_cai_bytes += cai_bytes
            
            gb_total = total_bytes / (1024**3)
            gb_cai = cai_bytes / (1024**3)

            print(f"  VOLUME (Last 30 Days):")
            print(f"  Total Ingest:  {gb_total:,.4f} GB")
            print(f"  CAI Metadata:  {gb_cai:,.4f} GB (included in total)")
            print("")
            
            print(f"  SINK CONFIGURATION:")
            print_sink_details(pid)
            
        else:
            # Failure/Skip Path
            projects_skipped += 1
            print("  [!] API Disabled or Permission Denied. (SKIPPED)")

    # --- Final Calculations ---
    # Convert bytes to GB and TB
    total_gb_30d = grand_total_bytes / (1024**3)
    total_tb_30d = grand_total_bytes / (1024**4)

    cai_gb_30d = grand_cai_bytes / (1024**3)
    cai_tb_30d = grand_cai_bytes / (1024**4)
    
    print("=" * 80)
    print("ORGANIZATION TOTALS")
    print("=" * 80)
    print(f"Projects Found:          {len(projects)}")
    print(f"Projects Scanned:        {projects_scanned}")
    print(f"Projects Skipped:        {projects_skipped}")
    print("-" * 40)
    print(f"TOTAL VOLUME (30 Days):  {total_tb_30d:,.4f} TB")
    print(f"                         ({total_gb_30d:,.2f} GB)")
    print("")
    print(f"  └─ CAI Portion:        {cai_tb_30d:,.4f} TB")
    print(f"                         ({cai_gb_30d:,.2f} GB)")
    print("=" * 80)