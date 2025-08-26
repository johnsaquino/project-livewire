# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Configuration for Vertex AI Gemini Multimodal Live Proxy Server
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass

def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get('PROJECT_ID')
    
    if not project_id:
        raise ConfigurationError("PROJECT_ID environment variable is not set")
    
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        raise


class ApiConfig:
    """API configuration handler."""
    
    def __init__(self):
        # Determine if using Vertex AI
        self.use_vertex = os.getenv('VERTEX_API', 'false').lower() == 'true'
        
        self.api_key: Optional[str] = None
        
        logger.info(f"Initialized API configuration with Vertex AI: {self.use_vertex}")
    
    async def initialize(self):
        """Initialize API credentials."""
        if not self.use_vertex:
            try:
                self.api_key = get_secret('GOOGLE_API_KEY')
            except Exception as e:
                logger.warning(f"Failed to get API key from Secret Manager: {e}")
                self.api_key = os.getenv('GOOGLE_API_KEY')
                if not self.api_key:
                    raise ConfigurationError("No API key available from Secret Manager or environment")

# Initialize API configuration
api_config = ApiConfig()

# Model configuration
if api_config.use_vertex:
    # Supported Live models: gemini-live-2.5-flash (Private GA), gemini-live-2.5-flash-preview-native-audio (Public preview)
    MODEL = os.getenv('MODEL_VERTEX_API', 'gemini-live-2.5-flash-preview-native-audio')
    VOICE = os.getenv('VOICE_VERTEX_API', 'Aoede')
else:
    MODEL = os.getenv('MODEL_DEV_API', 'models/gemini-live-2.5-flash-preview-native-audio')
    VOICE = os.getenv('VOICE_DEV_API', 'Puck')

# Cloud Function URLs (none by default). Leave a commented example for future use.
CLOUD_FUNCTIONS = {
    # Example template:
    # "my_example_tool": os.getenv('MY_EXAMPLE_TOOL_URL'),
}

# Validate Cloud Function URLs
for name, url in CLOUD_FUNCTIONS.items():
    if not url:
        logger.warning(f"Missing URL for cloud function: {name}")
    elif not url.startswith('https://'):
        logger.warning(f"Invalid URL format for {name}: {url}")

# Load system instructions
try:
    with open('config/system-instructions.txt', 'r') as f:
        SYSTEM_INSTRUCTIONS = f.read()
except Exception as e:
    logger.error(f"Failed to load system instructions: {e}")
    SYSTEM_INSTRUCTIONS = ""

logger.info(f"System instructions: {SYSTEM_INSTRUCTIONS}")

# Incremental summary / compaction settings
# Controls background summarization of long presentations to fit the Live API context.
INCREMENTAL_UPDATES_ENABLED = os.getenv('INCREMENTAL_UPDATES_ENABLED', 'true').lower() == 'true'
INCREMENTAL_SUMMARY_INTERVAL_SEC = int(os.getenv('INCREMENTAL_SUMMARY_INTERVAL_SEC', '60'))  # how often to update summary
INCREMENTAL_SUMMARY_MIN_CHARS = int(os.getenv('INCREMENTAL_SUMMARY_MIN_CHARS', '500'))      # minimum new chars to trigger an update
INCREMENTAL_SUMMARY_MAX_TOKENS = int(os.getenv('INCREMENTAL_SUMMARY_MAX_TOKENS', '1024'))   # cap summary size from generator
INCREMENTAL_SUMMARY_MODEL = os.getenv('INCREMENTAL_SUMMARY_MODEL', 'gemini-2.5-flash')      # text model for offline summarization
THOUGHTFUL_QUESTIONS_PROMPT = os.getenv('THOUGHTFUL_QUESTIONS_PROMPT',
    'Using the summary of the presentation, ask 3-5 thoughtful, specific questions that probe understanding, evidence, and implications. Keep them concise.').strip()

# A small, focused prompt the model uses to compress context.
INCREMENTAL_SUMMARY_PROMPT = os.getenv('INCREMENTAL_SUMMARY_PROMPT', """
You are maintaining a running, compact summary of a presentation so far.
- Summarize only what has been presented (no hallucinations).
- Preserve key claims, evidence, examples, and references to visuals if mentioned.
- Prefer bullet points. Keep under ~1000 words.
Return only the summary text (no preamble).
""").strip()

# Gemini Configuration (Multimodal Live)
# Note: Live API uses top-level response_modalities and speech_config; system_instruction is Content-like
CONFIG = {
    # Ask model to return audio
    "response_modalities": ["AUDIO"],
    # Select a prebuilt TTS voice
    "speech_config": {
        "voice_config": {
            "prebuilt_voice_config": {
                "voice_name": VOICE
            }
        }
    },
    "tools": [{
        "function_declarations": [
            # Example template (commented) to add a future tool:
            # {
            #     "name": "my_example_tool",
            #     "description": "Describe what the tool does",
            #     "parameters": {
            #         "type": "object",
            #         "properties": {
            #             "arg1": {
            #                 "type": "string",
            #                 "description": "Describe arg1"
            #             }
            #         },
            #         "required": ["arg1"]
            #     }
            # },
        ]
    }],
    # Convert system instructions into a Content-like structure if provided
    "system_instruction": (
        {"parts": [{"text": SYSTEM_INSTRUCTIONS}]} if SYSTEM_INSTRUCTIONS else None
    ),
    # Enable server-side transcriptions, used to build an incremental summary
    "input_audio_transcription": {},
    "output_audio_transcription": {},
}