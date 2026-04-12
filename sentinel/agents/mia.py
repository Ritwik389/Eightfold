"""
SENTINEL — Multimodal Integrity Agent (MIA)

Correlates video (lip aperture, gaze) and audio (VAD, energy) streams
to detect lip sync mismatches, gaze drift, and suspicious objects.
"""

import time
import logging
from dataclasses import asdict
from typing import Optional

from sentinel.config import (
    MIA_LIP_SYNC_MIN_GAP_MS,
    VOICE_WITHOUT_LIP_MOVEMENT_BONUS,
)
from sentinel.session_log import MIAEvent
from sentinel.utils.video import VideoMonitor, GazeDriftEvent, ObjectDetectedEvent
from sentinel.utils.audio import AudioMonitor

logger = logging.getLogger("sentinel.mia")


class MultimodalIntegrityAgent:
    """
    Correlates lip aperture and audio streams for integrity checks.
    Receives events from VideoMonitor and AudioMonitor.
    """

    def __init__(self, video_monitor: VideoMonitor, audio_monitor: AudioMonitor):
        self._video = video_monitor
        self._audio = audio_monitor
        self._events: list[MIAEvent] = []
        self._last_lip_check: float = 0.0

    def on_gaze_drift(self, event: GazeDriftEvent) -> None:
        """Handle a gaze drift event from VideoMonitor."""
        try:
            mia_event = MIAEvent(
                event_type="GAZE_DRIFT",
                timestamp_str=event.timestamp_str,
                snapshot_path=event.snapshot_path,
                confidence=min(1.0, event.duration / 5.0),
                note=(
                    f"Sustained gaze deviation for {event.duration:.1f}s. "
                    f"Gaze vector: ({event.gaze_x:.2f}, {event.gaze_y:.2f})."
                ),
            )
            self._events.append(mia_event)
            logger.info(f"MIA GAZE_DRIFT event at {event.timestamp_str}")
        except Exception as e:
            logger.error(f"Error handling gaze drift: {e}")

    def on_object_detected(self, event: ObjectDetectedEvent) -> None:
        """Handle an object detection event from VideoMonitor."""
        try:
            mia_event = MIAEvent(
                event_type="OBJECT_DETECTED",
                timestamp_str=event.timestamp_str,
                snapshot_path=event.snapshot_path,
                confidence=event.confidence,
                note=(
                    f"Detected '{event.class_name}' with confidence "
                    f"{event.confidence:.2f}."
                ),
            )
            self._events.append(mia_event)
            logger.info(
                f"MIA OBJECT_DETECTED: {event.class_name} "
                f"at {event.timestamp_str}"
            )
        except Exception as e:
            logger.error(f"Error handling object detection: {e}")

    def check_lip_sync(self) -> Optional[MIAEvent]:
        """
        Check for lip sync mismatches in the recent audio/video window.
        Called periodically or after each turn.

        Returns MIAEvent if mismatch detected, None otherwise.
        """
        if not self._video.is_available or not self._audio.is_available:
            return None

        try:
            window_ms = MIA_LIP_SYNC_MIN_GAP_MS
            audio_data = self._audio.get_recent_speech_state(window_ms=window_ms)
            lip_data = self._video.get_lip_apertures(
                since=time.time() - (window_ms / 1000.0)
            )

            if not audio_data or not lip_data:
                return None

            # Check if audio indicates speech but lips are closed
            speech_frames = [d for d in audio_data if d[2]]  # is_speech == True
            if not speech_frames:
                return None

            # Mean lip aperture during speech frames
            lip_apertures = [la.aperture for la in lip_data]
            if not lip_apertures:
                return None

            mean_aperture = sum(lip_apertures) / len(lip_apertures)
            mean_energy = sum(d[1] for d in speech_frames) / len(speech_frames)

            # Standard LIP_SYNC_MISMATCH
            if mean_aperture < 0.015 and len(speech_frames) > 5:
                gap_duration_ms = len(speech_frames) * 30  # 30ms per frame
                confidence = min(1.0, gap_duration_ms / 2000.0)

                snapshot_path = self._video.snapshot()

                # Determine if this is the stronger AUDIO_LIP_MISMATCH
                if mean_energy > 0.1 and mean_aperture < 0.01:
                    event_type = "AUDIO_LIP_MISMATCH"
                    note = (
                        f"Strong audio energy ({mean_energy:.3f} RMS) detected "
                        f"with completely closed lips (aperture {mean_aperture:.4f}). "
                        f"Duration: {gap_duration_ms}ms."
                    )
                else:
                    event_type = "LIP_SYNC_MISMATCH"
                    note = (
                        f"Speech detected but lip aperture low "
                        f"({mean_aperture:.4f}). "
                        f"Duration: {gap_duration_ms}ms."
                    )

                mia_event = MIAEvent(
                    event_type=event_type,
                    timestamp_str=time.strftime("%H:%M:%S"),
                    snapshot_path=snapshot_path,
                    confidence=confidence,
                    note=note,
                )
                self._events.append(mia_event)
                return mia_event

            return None

        except Exception as e:
            logger.debug(f"Lip sync check error: {e}")
            return None

    def check_composite_vsa_event(
        self, vsa_signal: str, vsa_distance: float
    ) -> Optional[MIAEvent]:
        """
        Check for composite VSA+MIA event: foreign voice + closed lips.

        Args:
            vsa_signal: VSA signal level (RED/AMBER/GREEN)
            vsa_distance: VSA cosine distance

        Returns:
            Composite MIAEvent if conditions met, None otherwise.
        """
        if vsa_signal != "RED":
            return None

        if not self._video.is_available:
            return None

        try:
            lip_data = self._video.get_lip_apertures(since=time.time() - 1.0)
            if not lip_data:
                return None

            mean_aperture = sum(la.aperture for la in lip_data) / len(lip_data)

            if mean_aperture < 0.015:
                snapshot_path = self._video.snapshot()
                event = MIAEvent(
                    event_type="VOICE_WITHOUT_LIP_MOVEMENT",
                    timestamp_str=time.strftime("%H:%M:%S"),
                    snapshot_path=snapshot_path,
                    confidence=min(1.0, vsa_distance * 2),
                    note=(
                        f"Foreign voice signature detected (cosine distance "
                        f"{vsa_distance:.3f}) simultaneously with closed lip "
                        f"landmarks (aperture {mean_aperture:.4f}). This "
                        f"combination is a high-confidence indicator of audio "
                        f"relay or earpiece assistance."
                    ),
                )
                self._events.append(event)
                return event

        except Exception as e:
            logger.debug(f"Composite VSA check error: {e}")

        return None

    @property
    def events(self) -> list[MIAEvent]:
        """Return all accumulated MIA events."""
        return list(self._events)

    def get_signal(self) -> str:
        """Return the worst signal from all events."""
        if not self._events:
            return "GREEN"

        # VOICE_WITHOUT_LIP_MOVEMENT and AUDIO_LIP_MISMATCH are always RED
        for event in self._events:
            if event.event_type in ("VOICE_WITHOUT_LIP_MOVEMENT",
                                     "AUDIO_LIP_MISMATCH"):
                return "RED"

        # Multiple events of any type = AMBER at least
        if len(self._events) >= 3:
            return "RED"
        elif len(self._events) >= 1:
            return "AMBER"

        return "GREEN"
