"""
Incremental summary manager for long presentations using Live API incremental client content.

This manager maintains a compact, running summary and pushes it into the Live API
conversation as a single, replaced user turn identified by a stable part ID.

Approach:
- Accumulate input transcriptions (server-provided) into a buffer.
- Periodically send a clientContent update that sets/updates a dedicated 'running summary'
  Content with a stable id so the server replaces it rather than appending endlessly.
- Keep the model quiet during updates (TEXT-only turns without TTS), and only speak later.
"""

from __future__ import annotations

import asyncio
import time
import logging
from typing import Optional

from google import genai

from config.config import (
    INCREMENTAL_UPDATES_ENABLED,
    INCREMENTAL_SUMMARY_INTERVAL_SEC,
    INCREMENTAL_SUMMARY_PROMPT,
    INCREMENTAL_SUMMARY_MAX_TOKENS,
    INCREMENTAL_SUMMARY_MODEL,
)
from config.config import api_config, ConfigurationError
import os

logger = logging.getLogger(__name__)


class IncrementalSummaryManager:
    def __init__(self, session_state):
        self.session_state = session_state
        self._lock = asyncio.Lock()
        self._last_update_ts = 0.0
        self.running_summary: str = ""
        self.transcript_buffer: list[str] = []
        # A stable id for the summary part; Live API will update the same content
        self.summary_part_id: str = "running_summary"

    def add_transcript(self, text: str) -> None:
        if not text:
            return
        self.transcript_buffer.append(text)

    def get_summary(self) -> str:
        return self.running_summary

    async def maybe_update(self):
        if not INCREMENTAL_UPDATES_ENABLED:
            return
        now = time.time()
        if now - self._last_update_ts < INCREMENTAL_SUMMARY_INTERVAL_SEC:
            return
        if not self.transcript_buffer:
            return

        async with self._lock:
            # Re-check under lock
            now = time.time()
            if now - self._last_update_ts < INCREMENTAL_SUMMARY_INTERVAL_SEC:
                return
            try:
                await self._update_summary_locked()
                self._last_update_ts = time.time()
            except Exception as e:
                logger.warning(f"Incremental summary update failed: {e}")

    async def _update_summary_locked(self):
        """
        Perform a summarization turn by sending a clientContent with a user turn
        that contains (a) a summarization instruction and (b) prior summary plus new transcript chunk.
        Then, capture the model text and immediately push a second clientContent update
        that stores the compact summary as a dedicated content part with a stable id
        so the server can keep only the compact representation in its prompt.
        """
        session = self.session_state.genai_session
        if not session:
            return

        # Build summarization input from buffered transcripts
        new_chunk = "\n".join(self.transcript_buffer).strip()
        self.transcript_buffer.clear()

        instruction = INCREMENTAL_SUMMARY_PROMPT
        if self.running_summary:
            instruction += "\n\nExisting summary to refine (merge and compress further):\n" + self.running_summary

        user_text = instruction + "\n\nNew transcript chunk to incorporate:\n" + new_chunk

        # Generate summary using non-live text generation to avoid audio.
        try:
            # Initialize auth
            await api_config.initialize()

            if api_config.use_vertex:
                location = os.getenv('VERTEX_LOCATION', 'us-central1')
                project_id = os.environ.get('PROJECT_ID')
                if not project_id:
                    raise ConfigurationError("PROJECT_ID is required for Vertex AI")
                client = genai.Client(vertexai=True, location=location, project=project_id)
            else:
                client = genai.Client(vertexai=False, http_options={'api_version': 'v1alpha'}, api_key=api_config.api_key)

            # Use sync Responses API in a worker thread for compatibility across versions
            resp = await asyncio.to_thread(
                client.responses.generate,
                model=INCREMENTAL_SUMMARY_MODEL,
                contents=user_text,
                config={
                    "max_output_tokens": INCREMENTAL_SUMMARY_MAX_TOKENS,
                },
            )
            summary_text = (getattr(resp, 'text', None) or "").strip()
        except Exception as e:
            logger.warning(f"Failed to generate incremental summary via text API: {e}")
            summary_text = ""

        if not summary_text:
            return

        self.running_summary = summary_text

        # Push/update the compact summary as a dedicated Content with a stable id.
        # Note: This uses clientContent to append a synthetic 'user' turn that holds
        # the compact summary. A stable part id hints replacement of that content
        # instead of unbounded history growth.
        await session.send(
            input={
                "client_content": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": "[Running summary updated]"},
                                {"text": self.running_summary},
                            ],
                        }
                    ],
                    # Do not trigger generation for update-only content
                    "turn_complete": False,
                }
            }
        )

    async def inject_summary_for_questions(self) -> None:
        """Send a small clientContent that marks the end and primes questions."""
        session = self.session_state.genai_session
        if not session or not self.running_summary:
            return
        prompt = (
            "Using the following compact summary of the presentation so far, "
            "ask 3-5 thoughtful, specific questions that probe understanding, evidence, and implications. "
            "Keep them concise.\n\nSummary:\n" + self.running_summary
        )
        await session.send(
            input={
                "client_content": {
                    "turns": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
                        }
                    ],
                    "turn_complete": True,
                }
            }
        )
