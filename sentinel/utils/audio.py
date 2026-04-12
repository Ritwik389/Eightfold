"""
SENTINEL — Audio Monitoring Utilities

VAD (Voice Activity Detection), energy envelope computation,
and heatmap data generation.

Supports two modes:
  1. WebRTC mode (primary): receives audio frames from streamlit-webrtc
  2. Fallback mode: captures from microphone via sounddevice/pyaudio
"""

import os
import threading
import struct
import time
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("sentinel.audio")

# Try to import VAD
_Vad = None
try:
    import webrtcvad
    _Vad = webrtcvad.Vad
    logger.info("webrtcvad loaded.")
except ImportError:
    logger.warning("webrtcvad not available — VAD disabled.")


class AudioMonitor:
    """
    Audio monitoring for SENTINEL.

    Primary mode: receives audio via process_audio_frames() from webrtc.
    Fallback mode: captures from mic via sounddevice daemon thread.
    """

    SAMPLE_RATE = 16000
    FRAME_DURATION_MS = 30
    FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)  # 480 samples

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._vad = None
        self._lock = threading.Lock()

        # Audio stream data for heatmap
        self._audio_data: list[tuple[float, float, bool]] = []

        # Turn-level audio buffer for VSA
        self._turn_buffer: list[np.ndarray] = []
        self._turn_buffer_lock = threading.Lock()
        self._recording_turn = False

        # Session start time
        self._start_time: float = 0.0

        # Mode flags
        self._webrtc_mode = False
        self._mic_available = False

    def _init_vad(self):
        """Initialise VAD if available."""
        if _Vad is not None:
            try:
                self._vad = _Vad(2)  # Aggressiveness mode 2
            except Exception as e:
                logger.warning(f"VAD init failed: {e}")
                self._vad = None

    # ══════════════════════════════════════════════════════
    # PRIMARY API — process audio from webrtc
    # ══════════════════════════════════════════════════════

    def process_audio_frames(self, audio_array: np.ndarray, sample_rate: int = 16000):
        """
        Process audio frames received from streamlit-webrtc.

        Args:
            audio_array: Audio samples as numpy array (any dtype).
            sample_rate: Sample rate of the audio.
        """
        self._mic_available = True

        try:
            # Convert to float32 normalised
            if audio_array.dtype == np.int16:
                audio_float = audio_array.astype(np.float32) / 32768.0
            elif audio_array.dtype == np.float32:
                audio_float = audio_array
            else:
                audio_float = audio_array.astype(np.float32)
                if audio_float.max() > 1.0:
                    audio_float = audio_float / 32768.0

            # If stereo, take first channel
            if len(audio_float.shape) > 1:
                audio_float = audio_float[:, 0] if audio_float.shape[1] > 1 else audio_float.flatten()

            # Resample if necessary (simple decimation)
            if sample_rate != self.SAMPLE_RATE and sample_rate > 0:
                ratio = sample_rate / self.SAMPLE_RATE
                if ratio > 1:
                    indices = np.arange(0, len(audio_float), ratio).astype(int)
                    indices = indices[indices < len(audio_float)]
                    audio_float = audio_float[indices]

            # Process in frame-sized chunks
            for i in range(0, len(audio_float) - self.FRAME_SIZE, self.FRAME_SIZE):
                chunk = audio_float[i:i + self.FRAME_SIZE]
                self._process_single_frame(chunk)

            # Add to turn buffer
            with self._turn_buffer_lock:
                if self._recording_turn:
                    self._turn_buffer.append(audio_float.copy())

        except Exception as e:
            logger.debug(f"Audio processing error: {e}")

    def _process_single_frame(self, audio_chunk: np.ndarray):
        """Process a single 30ms audio frame."""
        # Compute RMS energy
        energy = float(np.sqrt(np.mean(audio_chunk ** 2)))

        # Run VAD
        is_speech = False
        if self._vad is not None:
            try:
                # Convert to int16 bytes for VAD
                int16_data = (audio_chunk * 32768).astype(np.int16).tobytes()
                if len(int16_data) == self.FRAME_SIZE * 2:
                    is_speech = self._vad.is_speech(int16_data, self.SAMPLE_RATE)
            except Exception:
                # Energy-based fallback
                is_speech = energy > 0.02
        else:
            # No VAD: use energy threshold
            is_speech = energy > 0.02

        timestamp = time.time() - self._start_time

        with self._lock:
            self._audio_data.append((timestamp, energy, is_speech))

    # ══════════════════════════════════════════════════════
    # TURN BUFFERING
    # ══════════════════════════════════════════════════════

    def start_turn_recording(self):
        """Begin buffering audio for the current turn."""
        with self._turn_buffer_lock:
            self._turn_buffer = []
            self._recording_turn = True

    def stop_turn_recording(self) -> np.ndarray:
        """Stop buffering and return turn audio as float32 array [-1, 1]."""
        with self._turn_buffer_lock:
            self._recording_turn = False
            if not self._turn_buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._turn_buffer)
            self._turn_buffer = []
            return audio

    # ══════════════════════════════════════════════════════
    # QUERY METHODS
    # ══════════════════════════════════════════════════════

    def get_recent_speech_state(self, window_ms: int = 500) -> list[tuple[float, float, bool]]:
        """Get audio data from the last window_ms milliseconds."""
        if not self._audio_data:
            return []
        cutoff = time.time() - self._start_time - (window_ms / 1000.0)
        with self._lock:
            return [d for d in self._audio_data if d[0] >= cutoff]

    def heatmap_data(self) -> list[tuple[float, float, bool]]:
        """Returns (timestamp_seconds, energy, is_speech) for heatmap generation."""
        with self._lock:
            return list(self._audio_data)

    # ══════════════════════════════════════════════════════
    # STARTUP / SHUTDOWN
    # ══════════════════════════════════════════════════════

    def start(self) -> bool:
        """Start audio monitoring. Returns True if available."""
        self._start_time = time.time()
        self._init_vad()

        if self._webrtc_mode:
            self._mic_available = True
            self.start_turn_recording()
            return True

        # Fallback: try sounddevice
        try:
            import sounddevice as sd

            self._mic_available = True
            self._running = True
            self._thread = threading.Thread(target=self._run_sounddevice, daemon=True)
            self._thread.start()
            self.start_turn_recording()
            return True

        except ImportError:
            logger.warning("sounddevice not installed — audio disabled.")

        # Fallback: try pyaudio
        try:
            import pyaudio
            self._mic_available = True
            self._running = True
            self._thread = threading.Thread(target=self._run_pyaudio, daemon=True)
            self._thread.start()
            self.start_turn_recording()
            return True

        except ImportError:
            logger.warning("pyaudio not installed — audio disabled.")

        self._mic_available = False
        return False

    def set_webrtc_mode(self, enabled: bool = True):
        """Enable webrtc mode — audio comes via process_audio_frames()."""
        self._webrtc_mode = enabled
        self._mic_available = enabled

    def _run_sounddevice(self):
        """Capture audio via sounddevice (fallback mode)."""
        try:
            import sounddevice as sd
            with sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1,
                                dtype='float32', blocksize=self.FRAME_SIZE) as stream:
                while self._running:
                    data, _ = stream.read(self.FRAME_SIZE)
                    audio_chunk = data.flatten()
                    self._process_single_frame(audio_chunk)
                    with self._turn_buffer_lock:
                        if self._recording_turn:
                            self._turn_buffer.append(audio_chunk.copy())
        except Exception as e:
            logger.error(f"sounddevice capture error: {e}")
            self._mic_available = False

    def _run_pyaudio(self):
        """Capture audio via pyaudio (fallback mode)."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16, channels=1,
                rate=self.SAMPLE_RATE, input=True,
                frames_per_buffer=self.FRAME_SIZE,
            )
            while self._running:
                data = stream.read(self.FRAME_SIZE, exception_on_overflow=False)
                count = len(data) // 2
                shorts = struct.unpack(f"{count}h", data)
                audio_chunk = np.array(shorts, dtype=np.float32) / 32768.0
                self._process_single_frame(audio_chunk)
                with self._turn_buffer_lock:
                    if self._recording_turn:
                        self._turn_buffer.append(audio_chunk.copy())

            stream.stop_stream()
            stream.close()
            pa.terminate()
        except Exception as e:
            logger.error(f"pyaudio capture error: {e}")
            self._mic_available = False

    def stop(self):
        """Stop audio monitoring."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._mic_available = False

    @property
    def is_available(self) -> bool:
        return self._mic_available
