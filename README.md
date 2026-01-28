# gcp-secops-data-logging-ingest
Calculate the amount of Google Cloud logs data ingestion to be used for Google SecOps platform. 

This Python script will scan projects within your Google Cloud Organization and calculate the amount of data usage for Cloud Logging.

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
