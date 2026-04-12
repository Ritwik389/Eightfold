"""
SENTINEL — Voice Signature Agent (VSA)

Detects when a voice other than the registered candidate is audible.
Maintains a voiceprint baseline from the candidate's first 3 turns
and measures deviation of every subsequent audio segment.
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional, Callable

import numpy as np

from sentinel.config import (
    VSA_COSINE_THRESHOLDS,
    VSA_ENROLLMENT_TURNS,
    VSA_MFCC_FALLBACK_AMBER,
    VSA_MFCC_FALLBACK_RED,
    VSA_VOICE_DRIFT_THRESHOLD,
)
from sentinel.session_log import VSAEvent

logger = logging.getLogger("sentinel.vsa")


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine distance between two vectors. Range [0, 2]."""
    a = a.flatten()
    b = b.flatten()
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-9:
        return 1.0
    sim = np.dot(a, b) / denom
    return float(1.0 - sim)


class VoiceSignatureAgent:
    """
    Speaker verification agent using d-vector embeddings (resemblyzer)
    with MFCC fallback via librosa.
    """

    def __init__(self):
        self.baseline_embedding: Optional[np.ndarray] = None
        self.baseline_segments: list[np.ndarray] = []
        self.turn_embeddings: list[np.ndarray] = []
        self.anomaly_events: list[VSAEvent] = []
        self.enrollment_complete: bool = False
        self._turn_count: int = 0

        # Model handles
        self._voice_encoder = None
        self._use_mfcc_fallback = False
        self._model_loaded = False

        # Snapshot callback
        self._snapshot_fn: Optional[Callable] = None

    def set_snapshot_callback(self, fn: Callable) -> None:
        """Set the function to call for capturing video snapshots."""
        self._snapshot_fn = fn

    def _load_model(self):
        """Lazy-load the voice encoder model."""
        if self._model_loaded:
            return
        self._model_loaded = True

        try:
            from resemblyzer import VoiceEncoder
            self._voice_encoder = VoiceEncoder()
            logger.info("Resemblyzer VoiceEncoder loaded successfully.")
        except Exception as e:
            logger.warning(
                f"resemblyzer unavailable ({e}) — falling back to MFCC-based "
                f"speaker verification. Confidence is reduced."
            )
            self._use_mfcc_fallback = True
            self._voice_encoder = None

    def _embed_audio(self, audio: np.ndarray, sr: int = 16000) -> Optional[np.ndarray]:
        """
        Compute speaker embedding for an audio segment.

        Args:
            audio: Float32 audio array normalised to [-1, 1].
            sr: Sample rate.

        Returns:
            Embedding vector, or None on failure.
        """
        self._load_model()

        if len(audio) < sr * 0.5:  # Less than 500ms
            return None

        if self._voice_encoder is not None and not self._use_mfcc_fallback:
            try:
                embedding = self._voice_encoder.embed_utterance(audio)
                return embedding
            except Exception as e:
                logger.warning(f"d-vector embedding failed: {e} — using MFCC fallback")
                self._use_mfcc_fallback = True

        # MFCC fallback
        try:
            import librosa
            mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
            mean_mfcc = np.mean(mfccs, axis=1)
            # L2 normalise
            norm = np.linalg.norm(mean_mfcc)
            if norm > 1e-6:
                mean_mfcc = mean_mfcc / norm
            return mean_mfcc
        except Exception as e:
            logger.error(f"MFCC embedding failed: {e}")
            return None

    def _denoise_audio(self, audio: np.ndarray, sr: int = 16000) -> np.ndarray:
        """Apply noise reduction to raw audio."""
        try:
            import noisereduce as nr
            return nr.reduce_noise(y=audio, sr=sr, prop_decrease=0.8)
        except ImportError:
            logger.debug("noisereduce not available — skipping denoising")
            return audio
        except Exception:
            return audio

    def _vad_segment(self, audio: np.ndarray, sr: int = 16000) -> list[np.ndarray]:
        """
        Split audio into voiced segments using energy-based VAD.

        Returns segments of minimum 500ms duration.
        """
        try:
            import webrtcvad

            vad = webrtcvad.Vad(2)
            frame_duration_ms = 30
            frame_size = int(sr * frame_duration_ms / 1000)

            # Convert to int16 for VAD
            audio_int16 = (audio * 32768).astype(np.int16)
            raw_bytes = audio_int16.tobytes()

            segments = []
            current_segment = []
            is_speech_run = False

            for i in range(0, len(audio_int16) - frame_size, frame_size):
                frame = raw_bytes[i * 2: (i + frame_size) * 2]
                if len(frame) < frame_size * 2:
                    break

                try:
                    is_speech = vad.is_speech(frame, sr)
                except Exception:
                    is_speech = False

                if is_speech:
                    current_segment.extend(
                        audio[i: i + frame_size].tolist()
                    )
                    is_speech_run = True
                else:
                    if is_speech_run and len(current_segment) >= sr * 0.5:
                        segments.append(np.array(current_segment, dtype=np.float32))
                    current_segment = []
                    is_speech_run = False

            # Don't forget the last segment
            if is_speech_run and len(current_segment) >= sr * 0.5:
                segments.append(np.array(current_segment, dtype=np.float32))

            return segments

        except ImportError:
            # No VAD available — treat entire audio as one segment
            if len(audio) >= sr * 0.5:
                return [audio]
            return []
        except Exception as e:
            logger.debug(f"VAD segmentation error: {e}")
            if len(audio) >= sr * 0.5:
                return [audio]
            return []

    def analyse_turn_audio(
        self, audio: np.ndarray, sr: int = 16000
    ) -> dict:
        """
        Analyse a single turn's audio for voice signature anomalies.

        Args:
            audio: Raw PCM float32 array, normalised to [-1, 1]
            sr: Sample rate (default 16000)

        Returns:
            dict with keys: signal, events, enrollment_status
        """
        self._turn_count += 1
        result = {
            "signal": "GREEN",
            "events": [],
            "enrollment_status": "pending" if not self.enrollment_complete else "complete",
            "mean_distance": 0.0,
        }

        if len(audio) == 0:
            result["signal"] = "GREEN"
            return result

        try:
            # Step 1: Denoise
            audio = self._denoise_audio(audio, sr)

            # Step 2: VAD segmentation
            segments = self._vad_segment(audio, sr)
            if not segments:
                return result

            # Step 3: Embed each segment
            segment_embeddings = []
            for seg in segments:
                emb = self._embed_audio(seg, sr)
                if emb is not None:
                    segment_embeddings.append(emb)

            if not segment_embeddings:
                return result

            # Step 4: Enrollment phase (first N turns)
            if not self.enrollment_complete:
                self.baseline_segments.extend(segment_embeddings)

                if self._turn_count >= VSA_ENROLLMENT_TURNS:
                    if self.baseline_segments:
                        self.baseline_embedding = np.mean(
                            self.baseline_segments, axis=0
                        )
                        # L2 normalise
                        norm = np.linalg.norm(self.baseline_embedding)
                        if norm > 1e-6:
                            self.baseline_embedding /= norm
                        self.enrollment_complete = True
                        result["enrollment_status"] = "complete"
                        logger.info(
                            f"VSA enrollment complete after {self._turn_count} turns, "
                            f"{len(self.baseline_segments)} segments."
                        )

                return result

            # Step 5: Anomaly detection (post-enrollment)
            distances = []
            turn_events = []

            # Thresholds
            if self._use_mfcc_fallback:
                amber_thresh = VSA_MFCC_FALLBACK_AMBER
                red_thresh = VSA_MFCC_FALLBACK_RED
            else:
                amber_thresh = VSA_COSINE_THRESHOLDS["GREEN_MAX"]
                red_thresh = VSA_COSINE_THRESHOLDS["AMBER_MAX"]

            for i, emb in enumerate(segment_embeddings):
                dist = _cosine_distance(emb, self.baseline_embedding)
                distances.append(dist)

                if dist >= red_thresh:
                    signal = "RED"
                elif dist >= amber_thresh:
                    signal = "AMBER"
                else:
                    continue  # GREEN — no event

                # Classify anomaly type
                seg_audio = segments[i] if i < len(segments) else np.array([])
                anomaly_type = self._classify_anomaly(
                    seg_audio, dist, signal, sr
                )

                # Capture snapshot
                snapshot_path = None
                if self._snapshot_fn:
                    try:
                        snapshot_path = self._snapshot_fn()
                    except Exception:
                        pass

                # Compute segment timing
                seg_start_ms = int(i * 500)  # Approximate
                seg_end_ms = seg_start_ms + int(len(seg_audio) / sr * 1000)

                event = VSAEvent(
                    timestamp_str=time.strftime("%H:%M:%S"),
                    segment_start_ms=seg_start_ms,
                    segment_end_ms=seg_end_ms,
                    cosine_distance=round(dist, 4),
                    signal=signal,
                    anomaly_type=anomaly_type,
                    snapshot_path=snapshot_path,
                    note=self._build_note(signal, anomaly_type, dist),
                )
                turn_events.append(event)
                self.anomaly_events.append(event)

            # Store turn-level embedding (mean of all segments)
            turn_emb = np.mean(segment_embeddings, axis=0)
            self.turn_embeddings.append(turn_emb)

            # Determine turn signal
            mean_dist = float(np.mean(distances)) if distances else 0.0
            result["mean_distance"] = round(mean_dist, 4)
            result["events"] = turn_events

            if any(e.signal == "RED" for e in turn_events):
                result["signal"] = "RED"
            elif any(e.signal == "AMBER" for e in turn_events):
                result["signal"] = "AMBER"

            return result

        except Exception as e:
            logger.error(f"VSA analysis error: {e}")
            return result

    def _classify_anomaly(
        self,
        segment_audio: np.ndarray,
        distance: float,
        signal: str,
        sr: int,
    ) -> str:
        """Classify the type of voice anomaly."""
        try:
            # RMS energy
            rms = float(np.sqrt(np.mean(segment_audio ** 2))) if len(segment_audio) > 0 else 0.0
            duration_ms = int(len(segment_audio) / sr * 1000) if sr > 0 else 0

            # Whisper: low energy + high distance
            if rms < 0.015:
                return "WHISPER"

            # Voice relay: short, clean, high-confidence foreign voice
            if duration_ms < 800 and distance >= VSA_COSINE_THRESHOLDS.get("AMBER_MAX", 0.30):
                return "VOICE_RELAY"

            # Check for sustained foreign voice (multiple RED in window)
            recent_reds = [
                e for e in self.anomaly_events[-10:]
                if e.signal == "RED"
            ]
            if len(recent_reds) >= 2:
                return "SECONDARY_SPEAKER"

            return "UNKNOWN"

        except Exception:
            return "UNKNOWN"

    @staticmethod
    def _build_note(signal: str, anomaly_type: str, distance: float) -> str:
        """Build a human-readable note for the event."""
        type_descriptions = {
            "WHISPER": "Low energy voice detected — possible whispered prompt nearby.",
            "VOICE_RELAY": "Short foreign voice burst — consistent with earpiece relay pattern.",
            "SECONDARY_SPEAKER": "Sustained foreign voice presence detected.",
            "UNKNOWN": "Voice signature deviation of unknown origin.",
        }
        desc = type_descriptions.get(anomaly_type, "Voice anomaly detected.")
        return f"{signal}: {desc} Cosine distance: {distance:.3f}."

    def session_drift_check(self) -> Optional[VSAEvent]:
        """
        Session-level voice drift check.
        Compares mean cosine distance of final third vs first third of turns.

        Returns VSAEvent if drift detected, None otherwise.
        """
        if not self.enrollment_complete or len(self.turn_embeddings) < 6:
            return None

        try:
            n = len(self.turn_embeddings)
            third = n // 3

            first_dists = [
                _cosine_distance(emb, self.baseline_embedding)
                for emb in self.turn_embeddings[:third]
            ]
            last_dists = [
                _cosine_distance(emb, self.baseline_embedding)
                for emb in self.turn_embeddings[-third:]
            ]

            mean_last = float(np.mean(last_dists))

            if mean_last > VSA_VOICE_DRIFT_THRESHOLD:
                anomaly_type = ("SECONDARY_SPEAKER"
                                if mean_last > 0.30 else "VOICE_RELAY")

                snapshot_path = None
                if self._snapshot_fn:
                    try:
                        snapshot_path = self._snapshot_fn()
                    except Exception:
                        pass

                event = VSAEvent(
                    timestamp_str=time.strftime("%H:%M:%S"),
                    segment_start_ms=0,
                    segment_end_ms=0,
                    cosine_distance=round(mean_last, 4),
                    signal="RED",
                    anomaly_type=anomaly_type,
                    snapshot_path=snapshot_path,
                    note=(
                        f"Sustained speaker characteristic shift in final third "
                        f"of session. Mean distance: {mean_last:.3f} "
                        f"(threshold: {VSA_VOICE_DRIFT_THRESHOLD})."
                    ),
                )
                self.anomaly_events.append(event)
                return event

        except Exception as e:
            logger.error(f"Session drift check error: {e}")

        return None

    def get_report_data(self) -> dict:
        """Return data for report generation."""
        return {
            "enrollment_complete": self.enrollment_complete,
            "enrollment_turns": min(self._turn_count, VSA_ENROLLMENT_TURNS),
            "baseline_segments_count": len(self.baseline_segments),
            "turns_analysed": max(0, self._turn_count - VSA_ENROLLMENT_TURNS),
            "turn_distances": [
                round(
                    _cosine_distance(emb, self.baseline_embedding), 4
                )
                if self.baseline_embedding is not None else 0.0
                for emb in self.turn_embeddings
            ],
            "anomaly_events": [
                {
                    "timestamp_str": e.timestamp_str,
                    "segment_start_ms": e.segment_start_ms,
                    "segment_end_ms": e.segment_end_ms,
                    "cosine_distance": e.cosine_distance,
                    "signal": e.signal,
                    "anomaly_type": e.anomaly_type,
                    "note": e.note,
                }
                for e in self.anomaly_events
            ],
            "uses_mfcc_fallback": self._use_mfcc_fallback,
        }
