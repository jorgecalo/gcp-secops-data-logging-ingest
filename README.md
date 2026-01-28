# Google Cloud Logging data ingestion script for Google SecOps
Calculate the amount of Google Cloud logs (Cloud Logging) data ingestion to be used for Google SecOps platform. 

This Python script will scan projects within your Google Cloud Organization and calculate the amount of data used for Cloud Logging in the last 30 days. The scans includes the following logging types and Log Sink(s) configs: 

- Cloud Logging:
  Admin Activity audit logs,
  System Event audit logs,
  Google Workspace Admin Audit logs,
  Enterprise Groups Audit logs,
  Login Audit logs,
  Access Transparency logs

- Cloud Asset Metadata (CAI):
  Google Cloud asset metadata	
  GCP_BIGQUERY_CONTEXT,
  GCP_COMPUTE_CONTEXT,
  GCP_IAM_CONTEXT,
  GCP_IAM_ANALYSIS,	
  GCP_STORAGE_CONTEXT,	
  GCP_CLOUD_FUNCTIONS_CONTEXT,	
  GCP_SQL_CONTEXT,
  GCP_NETWORK_CONNECTIVITY_CONTEXT,	
  GCP_RESOURCE_MANAGER_CONTEXT.

When the script has run successfully you will get an overview of the amount of  scanned and skipped projects and the total monthly data ingestion for Cloud Logs with your organisation. Projects scanning might be limited due to disabled APIs or missing permissions. 

Send the output of the script to your sales or Customer Engineer.

# Required Packages
pip install google-cloud-logging google-cloud-monitoring google-cloud-service-usage google-cloud-resource-manager

# Enable Required APIs
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  serviceusage.googleapis.com

# Required Permissions
roles/resourcemanager.organizationViewer
roles/monitoring.viewer
roles/logging.configAccessor
roles/serviceusage.serviceUsageConsumer

# Run the script
/bin/python /home/admin_/gcp-secops-data-ingest.py
