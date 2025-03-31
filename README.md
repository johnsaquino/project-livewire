# Project Pastra

![Project Pastra](assets/project_pastra.png)

## Overview

Project Pastra is a modern multimodal chat application showcasing real-time voice, text, and visual interactions using Google's Gemini 2.0 Flash (experimental) and its Live API capabilities.  It offers a responsive web interface designed for both development and mobile use cases.

This project extends the concepts from the [Gemini Multimodal Live API Developer Guide](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide), providing production-ready features and enhanced capabilities.

### Key Features

- 🎤 Real-time voice interaction with AI.
- 💬 Text-based chat functionality.
- 📷 Webcam integration for visual context.
- 🖥️ Screen sharing capabilities.
- 🔊 High-quality audio streaming.
- 🛠️ Integrated tools for:
  - Weather information
  - Calendar management


### Gemini 2.0 Integration

- Multimodal Live API for real-time streaming.
- Low-latency responses with improved TTFT.
- Enhanced function calling and multi-tool capabilities.
- Bidirectional streaming with interruption support.
- Advanced processing of combined audio, video, and text inputs.

## Getting Started

This section provides a quickstart guide to get the application up and running. For more detailed information on specific components, refer to the README files located in the `client/` and `server/` directories.

### Prerequisites

- Python 3.8+
- API keys for:
  - Google Gemini API
  - OpenWeather API
  - Google Cloud credentials (if deploying to Google Cloud)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/heiko-hotz/project-pastra-v2.git
cd project-pastra-v2
```

### Quickstart

Choose one of the following options: Local Development or Deployment to Google Cloud Run.

#### 1. Local Development

Follow these steps to run the application locally:

1. **Configure Environment Variables:**

   ```bash
   # Navigate to the server directory
   cd server

   # Copy the example environment file
   cp .env.example .env

   # Edit .env with your actual API keys and configuration
   nano .env  # or use your preferred text editor
   ```

   The `.env.example` file contains required and optional environment variables.  At a minimum, set the following:

   - `PROJECT_ID`: Your Google Cloud project ID (if using Vertex API).
   - `VERTEX_LOCATION`: Your Google Cloud region (if using Vertex API).
   - `GOOGLE_API_KEY`: Your Gemini API key (if using Dev API).
   - `OPENWEATHER_API_KEY`: Your OpenWeather API key (if using weather tools).
   -  Cloud Function URLs for tool integrations (e.g. `WEATHER_FUNCTION_URL`, `FORECAST_FUNCTION_URL`, `CALENDAR_FUNCTION_URL`) - *Note: The tool integrations require cloud functions to be deployed seperately, for more details see the `server/README.md` file*

2. **Start the Backend Server:**

   ```bash
   # Make sure you're in the server directory
   cd server

   # Install dependencies
   pip install -r requirements.txt

   # Start the server
   python server.py
   ```

   The backend server will start on `localhost:8081`.

3. **Start the Frontend Client:**

   ```bash
   # Open a new terminal window
   # Navigate to the client directory
   cd client

   # Start a simple HTTP server
   python -m http.server 8000
   ```

4. **Access the Application:**

   Open your web browser and navigate to:

   - Development UI: `http://localhost:8000/index.html`
   - Mobile-optimized UI: `http://localhost:8000/mobile.html`

5. **Test the Connection:**

   1. Open your browser's developer tools (F12).
   2. Check the console for any connection errors.
   3. Try sending a test message through the interface.
   4. Verify that the WebSocket connection is established.

#### 2. Deploy to Google Cloud Run

This guide assumes you have the Google Cloud SDK (gcloud CLI) installed and configured.

1. **Configure Project and Enable APIs**

   If you haven't already, set your project ID:

   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

   Enable required APIs:

   ```bash
   gcloud services enable run.googleapis.com cloudbuild.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com iam.googleapis.com
   ```

2. **Create a Service Account for the Backend**

   ```bash
   gcloud iam service-accounts create pastra-backend \\
     --display-name="Pastra Backend Service Account"
   ```

3. **Grant Secret Manager Access to the Backend Service Account**

   ```bash
   gcloud projects add-iam-policy-binding \${PROJECT_ID} \\
     --member="serviceAccount:pastra-backend@\${PROJECT_ID}.iam.gserviceaccount.com" \\
     --role="roles/secretmanager.secretAccessor"
   ```

4. **Create Secrets in Secret Manager**

   Create the necessary secrets (replace `your-api-key` with the actual keys):

   ```bash
   gcloud secrets create GOOGLE_API_KEY --replication-policy="automatic"
   echo -n "your-api-key" | gcloud secrets versions add GOOGLE_API_KEY --data-file=-

   gcloud secrets create OPENWEATHER_API_KEY --replication-policy="automatic"
   echo -n "your-api-key" | gcloud secrets versions add OPENWEATHER_API_KEY --data-file=-

    #If using more APIs:
    #gcloud secrets create FINNHUB_API_KEY --replication-policy="automatic"
    #echo -n "your-api-key" | gcloud secrets versions add FINNHUB_API_KEY --data-file=-
   ```

5. **Deploy the Backend to Cloud Run**

   ```bash
   gcloud builds submit --config server/cloudbuild.yaml
   ```

   This command builds the Docker image for the backend and deploys it to Cloud Run. The `cloudbuild.yaml` file contains the deployment configuration.

6. **Deploy the Frontend to Cloud Run**

   ```bash
   #Get the backend url:
   BACKEND_URL=$(gcloud run services describe pastra-backend --platform managed --region us-central1 --format 'value(status.url)')

   # Deploy the Frontend to Cloud Run, passing the backend URL as a substitution variable:
   gcloud builds submit --config client/cloudbuild.yaml \\
     --substitutions=_BACKEND_URL=\$BACKEND_URL

   This command builds the Docker image for the frontend and deploys it to Cloud Run.  Before running this, make sure you update the `client/cloudbuild.yaml` with the URL of your newly deployed backend.

 7. **Access the Application**

   After deployment is complete, Cloud Run provides a URL for each service (frontend and backend). Access the frontend URL in your browser to use the application.

   ```bash
   gcloud run services describe pastra-ui --platform managed --region us-central1 --format 'value(status.url)'
   ```

### Troubleshooting Common Startup Issues

- See the "Local Development" section above for general troubleshooting.
- **Cloud Run deployment issues:** Check Cloud Build logs for build and deployment errors.  Ensure the service account used by Cloud Run has the necessary permissions.
- **Secret Manager access errors:**  Verify the service account has the `Secret Manager Secret Accessor` role.
- **Connectivity issues:** Ensure your Cloud Run services allow unauthenticated access (for basic testing).

## Architecture

![Architecture Overview](assets/architecture.png)

The architecture consists of:

- **Client:** The frontend web application, responsible for user interaction and media handling. Refer to the `client/README.md` (coming soon) for more details.
- **Server:**  A Python-based WebSocket server acting as a proxy and tool handler for the Gemini API. See the `server/README.md` file for detailed information.
- **Tools:**  Cloud Functions providing specific functionalities like weather, calendar, etc.
- **Gemini API:**  Google's AI model for processing requests and generating responses.

The diagram illustrates the key components and data flow. A user request flows through the Proxy, Gemini API, Tool Handler, and relevant Tools (e.g., Weather Agent), eventually returning a natural language response to the user. The system utilizes components such as the Proxy, Tool Handler, Weather Agent (running in Cloud Run), Secret Manager, and the Gemini Multimodal Live API, all hosted within Google Cloud Platform (GCP).

## Project Information

### License

This project is licensed under the Apache License.

### Contributing

This is a personal project, but suggestions and feedback are welcome! Feel free to open issues or submit pull requests. **Please note that this project is developed independently and does not reflect the views or efforts of Google.**

