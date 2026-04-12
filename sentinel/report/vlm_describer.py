"""
SENTINEL — VLM Describer

Uses Google Gemini 1.5 Pro (Vision) to describe snapshots
and audio heatmaps captured during the interview session.
"""

import time
import logging
from typing import Optional

from sentinel.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MAX_RETRIES, GEMINI_BACKOFF_BASE

logger = logging.getLogger("sentinel.vlm")

# Lazy-loaded Gemini model
_genai = None
_model = None


def _init_gemini():
    """Initialise the Gemini client (lazy)."""
    global _genai, _model
    if _model is not None:
        return

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _genai = genai
        _model = genai.GenerativeModel(GEMINI_MODEL)
        logger.info("Gemini VLM model initialised.")
    except Exception as e:
        logger.error(f"Failed to initialise Gemini: {e}")
        _model = None


def _call_gemini_with_retry(prompt: str, image=None) -> str:
    """
    Call Gemini with exponential backoff and retries.

    Args:
        prompt: Text prompt.
        image: Optional PIL Image for vision requests.

    Returns:
        Response text, or fallback message on failure.
    """
    _init_gemini()
    if _model is None:
        return "VLM description unavailable."

    for attempt in range(GEMINI_MAX_RETRIES):
        try:
            if image is not None:
                response = _model.generate_content([prompt, image])
            else:
                response = _model.generate_content(prompt)

            if response and response.text:
                return response.text.strip()
            return "VLM description unavailable."

        except Exception as e:
            wait = GEMINI_BACKOFF_BASE ** (attempt + 1)
            logger.warning(
                f"Gemini API call failed (attempt {attempt + 1}/{GEMINI_MAX_RETRIES}): "
                f"{e}. Retrying in {wait}s."
            )
            time.sleep(wait)

    return "VLM description unavailable."


class VLMDescriber:
    """
    Sends snapshots and heatmaps to Gemini 1.5 Pro for
    formal integrity analysis descriptions.
    """

    @staticmethod
    def describe_snapshot(
        snapshot_path: str, event_type: str, timestamp: str
    ) -> str:
        """
        Describe a snapshot image in the context of an integrity event.

        Args:
            snapshot_path: Path to the snapshot image on disk.
            event_type: Type of event that triggered capture.
            timestamp: When the snapshot was taken (HH:MM:SS).

        Returns:
            2-3 sentence formal description from Gemini.
        """
        try:
            from PIL import Image
            img = Image.open(snapshot_path)
        except Exception as e:
            logger.warning(f"Cannot open snapshot {snapshot_path}: {e}")
            return "VLM description unavailable — snapshot image could not be loaded."

        prompt = (
            f"You are an integrity review analyst examining a screenshot "
            f"captured during a technical interview at timestamp {timestamp}. "
            f"The automated system flagged this frame as a potential "
            f"{event_type} event. Describe in 2-3 formal sentences exactly "
            f"what you observe in the image that is relevant to this flag. "
            f"Be precise and objective. Do not speculate beyond what is visible. "
            f"Do not address the candidate. Write in third person."
        )

        return _call_gemini_with_retry(prompt, image=img)

    @staticmethod
    def describe_audio_heatmap(heatmap_image_path: str) -> str:
        """
        Describe an audio energy heatmap image.

        Args:
            heatmap_image_path: Path to the heatmap PNG.

        Returns:
            2-3 sentence formal description from Gemini.
        """
        try:
            from PIL import Image
            img = Image.open(heatmap_image_path)
        except Exception as e:
            logger.warning(f"Cannot open heatmap {heatmap_image_path}: {e}")
            return "VLM description unavailable — heatmap image could not be loaded."

        prompt = (
            "This is a temporal audio energy heatmap from a technical interview "
            "session. The x-axis represents time. The y-axis represents voice "
            "energy amplitude. Red regions indicate high energy (active speech). "
            "Blue regions indicate silence. Identify and describe in 2-3 formal "
            "sentences any regions where the energy pattern appears anomalous — "
            "for example, sustained high energy with abrupt uniform drops, or "
            "energy patterns inconsistent with natural conversational speech."
        )

        return _call_gemini_with_retry(prompt, image=img)

    @staticmethod
    def generate_executive_summary(session_data: dict) -> str:
        """
        Generate a 2-3 sentence executive integrity summary.

        Args:
            session_data: Serialised session log dict.

        Returns:
            Formal executive summary text.
        """
        import json
        data_str = json.dumps(session_data, indent=2, default=str)
        # Truncate if too long
        if len(data_str) > 8000:
            data_str = data_str[:8000] + "\n... [truncated]"

        prompt = (
            "Given the following session integrity data, write a 2-3 sentence "
            "formal executive summary for a human recruiter. State what signals "
            "were observed and what warrants review. Do not state a final conclusion.\n\n"
            f"Data: {data_str}"
        )

        return _call_gemini_with_retry(prompt)

    @staticmethod
    def generate_recruiter_guidance(session_data: dict) -> str:
        """
        Generate 3 bullet points of recruiter guidance.

        Args:
            session_data: Serialised session log dict.

        Returns:
            Recruiter guidance text as 3 bullet points.
        """
        import json
        data_str = json.dumps(session_data, indent=2, default=str)
        if len(data_str) > 8000:
            data_str = data_str[:8000] + "\n... [truncated]"

        prompt = (
            "Given the following interview integrity session data, generate "
            "exactly 3 bullet points of guidance for a human recruiter. "
            "Each bullet should be a full sentence. Focus on actionable next "
            "steps based on the signals observed. Do not make a final hiring "
            "recommendation.\n\n"
            f"Data: {data_str}"
        )

        return _call_gemini_with_retry(prompt)

    @staticmethod
    def generate_recruiter_note(event_data: dict) -> str:
        """
        Generate a one-sentence recruiter note for a specific event.

        Args:
            event_data: Dict with event details.

        Returns:
            One-sentence note for the recruiter.
        """
        import json
        data_str = json.dumps(event_data, indent=2, default=str)

        prompt = (
            "Given this integrity event detected during a technical interview, "
            "write exactly one sentence as a note for the recruiter explaining "
            "what this event might indicate and what to look for in follow-up. "
            "Be objective and measured.\n\n"
            f"Event: {data_str}"
        )

        return _call_gemini_with_retry(prompt)

    @staticmethod
    def generate_section_assessment(
        section_name: str, section_data: dict
    ) -> str:
        """
        Generate a 2-sentence assessment for a report section.

        Args:
            section_name: Name of the analysis section.
            section_data: Relevant data for the section.

        Returns:
            2-sentence formal assessment.
        """
        import json
        data_str = json.dumps(section_data, indent=2, default=str)
        if len(data_str) > 4000:
            data_str = data_str[:4000] + "\n... [truncated]"

        prompt = (
            f"Given the following {section_name} data from a technical interview "
            f"integrity analysis, write exactly 2 formal sentences assessing "
            f"what the data indicates. Be objective and precise.\n\n"
            f"Data: {data_str}"
        )

        return _call_gemini_with_retry(prompt)
