"""
Google Cloud Text-to-Speech Integration

Converts interviewer questions to speech for audio playback.
Uses Google Cloud's neural voices for natural-sounding speech.
"""

import os
import logging
from typing import Optional

from google.cloud import texttospeech

logger = logging.getLogger("google_tts")


class GoogleTTS:
    """Text-to-Speech using Google Cloud API."""
    
    def __init__(self):
        # Requires GOOGLE_APPLICATION_CREDENTIALS env var pointing to service account JSON
        try:
            self.client = texttospeech.TextToSpeechClient()
        except Exception as e:
            logger.warning(f"Google TTS initialization failed: {e}. Using mock TTS.")
            self.client = None
        
        # Voice configuration
        self.voice_language = "en-US"
        self.voice_name = "en-US-Neural2-A"  # Professional female voice
        self.audio_encoding = texttospeech.AudioEncoding.MP3
        self.speaking_rate = 1.0  # Normal speed
        self.pitch = 0.0  # Normal pitch
    
    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: float = 1.0
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: Question/statement to synthesize
            voice: Voice name override (optional)
            rate: Speaking rate (0.25-4.0, default 1.0)
        
        Returns:
            MP3 audio bytes
        """
        if not self.client:
            logger.warning("Google TTS not available - returning mock audio")
            return self._mock_audio()
        
        try:
            # Text input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Voice selection
            voice_config = texttospeech.VoiceSelectionParams(
                language_code=self.voice_language,
                name=voice or self.voice_name,
            )
            
            # Audio config
            audio_config = texttospeech.AudioConfig(
                audio_encoding=self.audio_encoding,
                speaking_rate=rate,
                pitch=self.pitch,
            )
            
            # Request
            request = texttospeech.SynthesizeSpeechRequest(
                input=synthesis_input,
                voice=voice_config,
                audio_config=audio_config,
            )
            
            # Synthesize
            response = self.client.synthesize_speech(request=request)
            
            logger.info(f"Synthesized audio for: {text[:50]}...")
            
            return response.audio_content
        
        except Exception as e:
            logger.error(f"Google TTS synthesis error: {e}")
            raise
    
    def _mock_audio(self) -> bytes:
        """Return mock MP3 data for offline development."""
        # Minimal MP3 header + silence (just for dev/testing)
        return b'\xff\xfb' + b'\x00' * 1000
    
    @staticmethod
    def list_voices() -> list:
        """List available voices (for frontend selection)."""
        try:
            client = texttospeech.TextToSpeechClient()
            response = client.list_voices(language_code="en-US")
            
            voices = []
            for voice in response.voices:
                voices.append({
                    "name": voice.name,
                    "language_codes": list(voice.language_codes),
                    "ssml_gender": voice.ssml_gender.name,
                })
            
            return voices
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []
