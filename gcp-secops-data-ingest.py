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
    from google.cloud.logging_v2.services.config_service_v2 import ConfigServiceV2Client
except ImportError as e:
    print("CRITICAL ERROR: Missing required Google Cloud libraries.")
    print(f"Details: {e}")
    print("\nPlease run the following command to install them:")
    print("pip install google-cloud-logging google-cloud-monitoring google-cloud-service-usage google-cloud-resource-manager")
    sys.exit(1)

def get_projects_in_org(org_id):
    """
    Lists all ACTIVE projects within the Organization, including projects
    nested in folders (walked recursively).
    """
    print(f"Searching for active projects in Org ID: {org_id}...")
    projects_client = resourcemanager_v3.ProjectsClient()
    folders_client = resourcemanager_v3.FoldersClient()
    active = resourcemanager_v3.Project.State.ACTIVE
    projects = []

    # Breadth-first walk: the org itself, then every folder below it.
    parents = [f"organizations/{org_id}"]
    try:
        while parents:
            parent = parents.pop(0)
            for project in projects_client.list_projects(parent=parent):
                if project.state == active:
                    projects.append(project.project_id)
            try:
                for folder in folders_client.list_folders(parent=parent):
                    parents.append(folder.name)
            except Exception as e:
                print(f"  [!] Could not list folders under {parent}: {e}")
                print("      Projects inside those folders will be missing from the totals.")

    except Exception as e:
        print(f"\n[!] Error listing projects: {e}")
        print("Tip: Ensure your account has 'Organization Viewer' and 'Folder Viewer' permissions.")
        sys.exit(1)

    print(f"Found {len(projects)} active projects.")
    return projects

def check_api_status(client, project_id):
    """
    Checks if Cloud Monitoring API is enabled.
    """
    service_name = f"projects/{project_id}/services/monitoring.googleapis.com"
    try:
        request = service_usage_v1.GetServiceRequest(name=service_name)
        response = client.get_service(request=request)
        return response.state == service_usage_v1.State.ENABLED
    except Exception:
        return False

def get_volume(client, project_id, specific_log_filter=None):
    """
    Returns the bytes ingested over the last 30 days, or None if the
    metric could not be read.
    """
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
            if not result.points:
                continue
            # The whole window is a single alignment period. If the API ever
            # returns more than one point, only the newest one covers exactly
            # the last 30 days; summing them would double count.
            latest = max(result.points, key=lambda p: p.interval.end_time)
            total += latest.value.int64_value
        return total
    except Exception as e:
        print(f"  [!] Could not read log volume metric: {e}")
        return None

def print_sink_details(client, project_id):
    """
    Fetches and prints Log Router Sinks for a project.
    """
    try:
        sinks = list(client.list_sinks(parent=f"projects/{project_id}"))
        
        if not sinks:
            print(f"     [i] No Log Sinks configured.")
            return

        for sink in sinks:
            print(f"     > Sink Name:       {sink.name}")
            print(f"       Writer Identity: {sink.writer_identity or '(none)'}")
            print(f"       Destination:     {sink.destination}")
            if sink.disabled:
                print(f"       Status:          DISABLED")

            inc_filter = sink.filter if sink.filter else "(All Logs)"
            if len(inc_filter) > 80: inc_filter = inc_filter[:77] + "..."
            print(f"       Inclusion Filt:  {inc_filter}")

            if sink.exclusions:
                print(f"       Exclusions:      {len(sink.exclusions)} found")
                for ex in sink.exclusions:
                    ex_filter = ex.filter if len(ex.filter) <= 60 else ex.filter[:57] + "..."
                    state = " (disabled)" if ex.disabled else ""
                    print(f"         - {ex.name}{state}: {ex_filter}")
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

    if not org_id.isdigit():
        print("[!] Error: The Organization ID must be a number, e.g. 123456789.")
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
    projects_metric_errors = 0

    # Create API clients once and reuse them for every project.
    usage_client = service_usage_v1.ServiceUsageClient()
    metric_client = monitoring_v3.MetricServiceClient()
    sink_client = ConfigServiceV2Client()
    
    print("\nProcessing projects... (This may take a moment)\n")

    for pid in projects:
        print("-" * 80)
        print(f"PROJECT: {pid}")
        print("-" * 80)

        if check_api_status(usage_client, pid):
            # Success Path
            projects_scanned += 1
            
            # 1. Get TOTAL Volume
            total_bytes = get_volume(metric_client, pid)
            cai_bytes = get_volume(metric_client, pid, specific_log_filter="cloudasset.googleapis.com/temporal_asset")
            if total_bytes is None or cai_bytes is None:
                projects_metric_errors += 1
            total_bytes = total_bytes or 0
            cai_bytes = cai_bytes or 0

            grand_total_bytes += total_bytes
            grand_cai_bytes += cai_bytes
            
            gb_total = total_bytes / (1000**3)
            gb_cai = cai_bytes / (1000**3)

            print(f"  VOLUME (Last 30 Days):")
            print(f"  Total Ingest:  {gb_total:,.4f} GB")
            print(f"  CAI Metadata:  {gb_cai:,.4f} GB (included in total)")
            print("")
            
            print(f"  SINK CONFIGURATION:")
            print_sink_details(sink_client, pid)
            
        else:
            # Failure/Skip Path
            projects_skipped += 1
            print("  [!] API Disabled or Permission Denied. (SKIPPED)")

    # --- Final Calculations ---
    # Convert bytes to decimal GB (10^9 bytes) and TB (10^12 bytes)
    total_gb_30d = grand_total_bytes / (1000**3)
    total_tb_30d = grand_total_bytes / (1000**4)

    cai_gb_30d = grand_cai_bytes / (1000**3)
    cai_tb_30d = grand_cai_bytes / (1000**4)
    
    print("=" * 80)
    print("ORGANIZATION TOTALS")
    print("=" * 80)
    print(f"Projects Found:          {len(projects)}")
    print(f"Projects Scanned:        {projects_scanned}")
    print(f"Projects Skipped:        {projects_skipped}")
    if projects_metric_errors:
        print(f"Metric Read Errors:      {projects_metric_errors} (counted as 0 bytes)")
    print("-" * 40)
    print(f"TOTAL VOLUME (30 Days):  {total_tb_30d:,.4f} TB")
    print(f"                         ({total_gb_30d:,.2f} GB)")
    print("")
    print(f"  └─ CAI Portion:        {cai_tb_30d:,.4f} TB")
    print(f"                         ({cai_gb_30d:,.2f} GB)")
    print("=" * 80)