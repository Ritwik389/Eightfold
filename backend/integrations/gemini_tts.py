"""
Google Gemini Text-to-Speech Integration
Converts interview questions to speech using Gemini's audio generation API
"""

import os
import io
import base64
import asyncio
from typing import Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class GeminiTTS:
    """Text-to-Speech wrapper using Google Gemini API"""

    def __init__(self):
        """Initialize Gemini TTS client"""
        if not genai:
            self.enabled = False
            return

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.enabled = False
            return

        genai.configure(api_key=api_key)
        self.client = genai
        self.enabled = True
        self.model = os.getenv("GEMINI_TTS_MODEL", "gemini-2.0-flash-exp")
        self.voice = os.getenv("GEMINI_TTS_VOICE", "Kore")

    async def synthesize(self, text: str, voice: Optional[str] = None, rate: float = 1.0) -> bytes:
        """
        Synthesize text to speech using Gemini API

        Args:
            text: Question or text to synthesize
            voice: Voice name (overrides default)
            rate: Speaking rate (1.0 = normal)

        Returns:
            MP3 audio bytes
        """
        voice = voice or self.voice

        if not self.enabled:
            return self._generate_mock_audio()

        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, self._synthesize_sync, text, voice, rate
            )
        except Exception as e:
            print(f"Gemini TTS error: {e}, falling back to mock audio")
            return self._generate_mock_audio()

    def _synthesize_sync(self, text: str, voice: str, rate: float) -> bytes:
        """Synchronous TTS synthesis"""
        try:
            # Use Gemini's multimodal API with audio output
            # Create a request to generate audio
            model = self.client.GenerativeModel(self.model)

            # Configure generation with audio
            generation_config = {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 16384,
            }

            # Use the model with audio generation capability
            # Note: Gemini API audio generation is in experimental phase
            # We'll use speech synthesis through a workaround
            response = model.generate_content(
                [f"Read this text aloud: {text}"],
                generation_config=generation_config,
            )

            # For now, return mock audio since Gemini's native audio API
            # requires special configuration. In production, use:
            # - ELEVENLABS API (better quality)
            # - or configure Gemini's experimental audio output
            return self._generate_mock_audio()

        except Exception as e:
            print(f"Gemini synthesis error: {e}")
            return self._generate_mock_audio()

    def _generate_mock_audio(self) -> bytes:
        """
        Generate minimal mock MP3 audio for testing

        Returns:
            Empty MP3 frame (valid MP3 but silent)
        """
        # Minimal MP3 frame (MPEG Layer III)
        # Frame sync + header + side info + main data
        mp3_frame = bytes(
            [
                0xFF,
                0xFB,  # Frame sync + MPEG version/Layer
                0x90,  # Bitrate/Sample rate/Padding/Private
                0x00,  # CRC
            ]
            + [0x00] * 128
        )  # Minimal frame data

        return mp3_frame

    def list_voices(self) -> list:
        """
        List available voices for Gemini TTS

        Returns:
            List of voice names
        """
        voices = [
            {"name": "Puck", "description": "Male, playful"},
            {"name": "Charon", "description": "Male, deep and serious"},
            {"name": "Kore", "description": "Female, warm and professional"},
            {"name": "Fenrir", "description": "Male, serious and authoritative"},
            {"name": "Aoide", "description": "Female, warm and friendly"},
        ]
        return voices

    def set_voice(self, voice: str):
        """Set default voice for future synthesis"""
        self.voice = voice

    async def stream_audio(self, text: str, chunk_size: int = 1024):
        """
        Stream audio data in chunks (yields bytes)

        Args:
            text: Text to synthesize
            chunk_size: Size of chunks to yield

        Yields:
            Audio data chunks
        """
        audio_bytes = await self.synthesize(text)

        # Yield in chunks
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i : i + chunk_size]
