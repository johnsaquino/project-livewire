# Cloud Function Tools

This directory contains various tools that are deployed as Google Cloud Functions.

## Tools Overview

### Example Tools
- This folder previously included a sample weather tool. You can replace it with your own Cloud Function tools as needed.

## Prerequisites

1. **Google Cloud Project Setup**:
   ```bash
   # Set your project ID
   export PROJECT_ID=your-project-id
   gcloud config set project $PROJECT_ID
   ```

2. **Enable Required APIs**:
   ```bash
   gcloud services enable \
     cloudfunctions.googleapis.com \
     secretmanager.googleapis.com \
     calendar-json.googleapis.com
   ```

## Secret Management Setup

1. **Create Service Account for Functions**:
   ```bash
   # Create service account for weather functions
   gcloud iam service-accounts create weather-function-sa \
       --description="Service account for Weather Cloud Functions" \
       --display-name="Weather Function SA"
   ```

2. **Grant Secret Manager Access**:
   ```bash
   # Grant access to weather function service account
   gcloud projects add-iam-policy-binding $PROJECT_ID \
       --member="serviceAccount:weather-function-sa@$PROJECT_ID.iam.gserviceaccount.com" \
       --role="roles/secretmanager.secretAccessor"
   ```

3. **Store any tool secrets in Secret Manager** as required by your function.

## Example Deployment

Deploy your own function(s) per their language/runtime guide. Example:
```bash
gcloud functions deploy my-example-tool \
   --runtime python312 \
   --trigger-http \
   --entry-point=handler \
   --service-account="weather-function-sa@$PROJECT_ID.iam.gserviceaccount.com" \
   --source=cloud-functions/weather-tools/my-example-tool \
   --region=us-central1
```

## Testing the Functions

```bash
# Example test call
curl "https://YOUR_FUNCTION_URL/my-example-tool?arg1=value"
```

## Project Structure
```
cloud-functions/
├── weather-tools/
│   └── my-example-tool/
│       ├── main.py
│       └── requirements.txt
```

## Security Notes
- Never commit API keys or service account credentials to version control
- Use Secret Manager for all sensitive credentials
- Consider adding authentication to your Cloud Functions if needed
- Regularly rotate API keys and service account credentials
- Monitor function access logs for any suspicious activity 