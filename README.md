# Google Cloud Logging Ingest Estimator for Google SecOps

Estimate how much Google Cloud log data (Cloud Logging) your organization would send to the **Google SecOps** platform.

The Python script scans every active project in your Google Cloud organization, including projects nested in folders. For each project it reports the Cloud Logging volume of the **last 30 days** and the Log Router sink configuration.

> [!NOTE]
> This is not an official Google tool. The numbers are an estimate based on Cloud Monitoring metrics and do not replace your Google Cloud invoice.

---

## What gets measured

The script reads the `logging.googleapis.com/byte_count` metric per project. That total covers **all** logs ingested into Cloud Logging for the project, so treat it as an upper bound for what SecOps would ingest.

Cloud Asset Inventory (CAI) metadata is also reported on its own line. It is already included in the total.

All sizes use decimal units: 1 GB is 1,000,000,000 bytes and 1 TB is 1,000 GB.

### Log types relevant to Google SecOps

| Cloud Logging | Cloud Asset Metadata (CAI) |
| --- | --- |
| Admin Activity audit logs | `GCP_BIGQUERY_CONTEXT` |
| System Event audit logs | `GCP_COMPUTE_CONTEXT` |
| Google Workspace Admin Audit logs | `GCP_IAM_CONTEXT` |
| Enterprise Groups Audit logs | `GCP_IAM_ANALYSIS` |
| Login Audit logs | `GCP_STORAGE_CONTEXT` |
| Access Transparency logs | `GCP_CLOUD_FUNCTIONS_CONTEXT` |
| | `GCP_SQL_CONTEXT` |
| | `GCP_NETWORK_CONNECTIVITY_CONTEXT` |
| | `GCP_RESOURCE_MANAGER_CONTEXT` |

---

## Prerequisites

### 1. Python and packages

Python 3.10 or newer is recommended.

```bash
pip install google-cloud-logging google-cloud-monitoring google-cloud-service-usage google-cloud-resource-manager
```

### 2. Enable the required APIs

```bash
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  serviceusage.googleapis.com
```

### 3. Grant the required roles

Grant these roles at the **organization** level to the account that runs the script.

| Role | Used for |
| --- | --- |
| `roles/resourcemanager.organizationViewer` | Reading the organization |
| `roles/resourcemanager.folderViewer` | Finding projects inside folders |
| `roles/monitoring.viewer` | Reading log volume metrics |
| `roles/logging.configAccessor` | Reading Log Router sinks |
| `roles/serviceusage.serviceUsageConsumer` | Checking whether the Monitoring API is enabled |

### 4. Authenticate

```bash
gcloud auth application-default login
```

---

## Run the script

```bash
python3 gcp-secops-data-ingest.py
```

The script asks you to accept the disclaimer and then to enter your numeric **Organization ID**. You can find it with:

```bash
gcloud organizations list
```

---

## Output

For each project you get:

- **Total Ingest.** Log volume of the last 30 days, in decimal GB.
- **CAI Metadata.** The Cloud Asset Inventory share of that volume.
- **Sink Configuration.** Every Log Router sink with its destination, inclusion filter and exclusions.

At the end the script prints the **organization totals**. It also shows how many projects were scanned and how many were skipped. A project is skipped when the Monitoring API is disabled or permissions are missing.

If a project's volume metric cannot be read, for example because of a quota error, the script prints a warning. That project counts as 0 bytes, and a **Metric Read Errors** line appears in the totals. Rerun the script if you see it.

```text
================================================================================
ORGANIZATION TOTALS
================================================================================
Projects Found:          42
Projects Scanned:        40
Projects Skipped:        2
----------------------------------------
TOTAL VOLUME (30 Days):  1.2345 TB
                         (1,234.50 GB)

  └─ CAI Portion:        0.0123 TB
                         (12.30 GB)
================================================================================
```

📨 **Send the output to your Google Sales representative or Customer Engineer.**

---

## Disclaimer

This script is provided for informational purposes only and is not an official Google product. You use it at your own risk. The authors are not liable for any errors, omissions or damages arising from its use. Always refer to your official Google Cloud invoice for exact charges.
