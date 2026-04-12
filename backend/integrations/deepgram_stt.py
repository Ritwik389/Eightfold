"""
Deepgram STT Integration

Transcribes audio using Deepgram's Speech-to-Text API.
Supports real-time and batch transcription with accuracy optimization.
"""

import os
import logging
from typing import Optional

from deepgram import DeepgramClient, PrerecordedOptions

logger = logging.getLogger("deepgram_stt")


class DeepgramSTT:
    """Speech-to-Text using Deepgram SDK."""
    
    def __init__(self):
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY not set in environment")
        
        self.client = DeepgramClient(api_key=api_key)
        self.model = "nova-2"  # Latest, most accurate model
    
    async def transcribe(
        self,
        audio_bytes: bytes,
        language: str = "en",
        enable_punctuation: bool = True,
        enable_diarization: bool = False
    ) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio data (WebM, WAV, MP3, etc.)
            language: Language code (default: English)
            enable_punctuation: Add punctuation to transcript
            enable_diarization: Separate speakers (for interview: candidate vs background)
        
        Returns:
            Transcribed text from the audio
        """
        try:
            # Configure transcription options
            options = PrerecordedOptions(
                model=self.model,
                language=language,
                punctuate=enable_punctuation,
                diarize=enable_diarization,
                smart_format=True,  # Format numbers, dates, etc.
            )
            
            # Transcribe
            response = self.client.listen.prerecorded.transcribe_file(
                {"buffer": audio_bytes},
                options,
            )
            
            # Extract transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            
            logger.info(f"Transcribed: {transcript[:100]}...")
            
            return transcript
        
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}")
            raise
    
    async def transcribe_stream(
        self,
        audio_stream,
        language: str = "en"
    ) -> str:
        """
        Transcribe streaming audio (for live recording).
        
        Args:
            audio_stream: Iterator of audio chunks
            language: Language code
        
        Returns:
            Full transcript
        """
        try:
            options = PrerecordedOptions(
                model=self.model,
                language=language,
                punctuate=True,
            )
            
            response = self.client.listen.prerecorded.transcribe_stream(
                audio_stream,
                options,
            )
            
            transcript = response.results.channels[0].alternatives[0].transcript
            return transcript
        
        except Exception as e:
            logger.error(f"Deepgram stream transcription error: {e}")
            raise
