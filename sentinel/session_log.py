"""
SENTINEL Session Log — In-memory + disk session state.
Holds all data for a single interview session.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from sentinel.config import (
    INTEGRITY_THRESHOLDS,
    LATE_SESSION_WEIGHT_MULTIPLIER,
    REPORT_DIR,
)


@dataclass
class TurnRecord:
    """Record for a single interview turn."""
    turn_index: int
    question: str
    response: str
    timestamp: str  # ISO 8601
    lca_result: dict = field(default_factory=dict)
    sda_result: dict = field(default_factory=dict)
    eca_result: dict = field(default_factory=dict)
    aiga_result: dict = field(default_factory=dict)
    vsa_result: dict = field(default_factory=dict)
    integrity_score: float = 0.0
    classification: str = "CLEAN"


@dataclass
class MIAEvent:
    """A multimodal integrity event detected during the session."""
    event_type: str         # GAZE_DRIFT | LIP_SYNC_MISMATCH | OBJECT_DETECTED | AUDIO_LIP_MISMATCH | VOICE_WITHOUT_LIP_MOVEMENT
    timestamp_str: str      # HH:MM:SS
    snapshot_path: str = ""
    confidence: float = 0.0
    note: str = ""


@dataclass
class VSAEvent:
    """A voice signature anomaly event."""
    timestamp_str: str           # HH:MM:SS
    segment_start_ms: int = 0
    segment_end_ms: int = 0
    cosine_distance: float = 0.0
    signal: str = "GREEN"        # AMBER | RED
    anomaly_type: str = "UNKNOWN"  # SECONDARY_SPEAKER | WHISPER | VOICE_RELAY | UNKNOWN
    snapshot_path: Optional[str] = None
    note: str = ""


class SessionLog:
    """
    Holds all session state. Instantiated once per interview session.
    """

    def __init__(self, candidate_name: str = "", experience_tier: str = "Mid-level"):
        self.candidate_name: str = candidate_name
        self.experience_tier: str = experience_tier
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.turns: list[TurnRecord] = []
        self.mia_events: list[MIAEvent] = []
        self.vsa_events: list[VSAEvent] = []
        self.integrity_scores: list[float] = []
        self.snapshot_paths: list[str] = []

    def add_turn(self, turn_record: TurnRecord) -> None:
        """Append a completed turn record."""
        self.turns.append(turn_record)
        self.integrity_scores.append(turn_record.integrity_score)

    def add_mia_event(self, mia_event: MIAEvent) -> None:
        """Append a multimodal integrity event."""
        self.mia_events.append(mia_event)

    def add_vsa_event(self, vsa_event: VSAEvent) -> None:
        """Append a voice signature event."""
        self.vsa_events.append(vsa_event)

    def session_integrity_score(self) -> float:
        """
        Weighted average of integrity_scores,
        applying LATE_SESSION_WEIGHT_MULTIPLIER to the final third.
        """
        if not self.integrity_scores:
            return 0.0

        n = len(self.integrity_scores)
        cutoff = max(1, n - (n // 3))  # Start of final third

        weighted_sum = 0.0
        weight_total = 0.0

        for i, score in enumerate(self.integrity_scores):
            w = LATE_SESSION_WEIGHT_MULTIPLIER if i >= cutoff else 1.0
            weighted_sum += score * w
            weight_total += w

        return min(100.0, weighted_sum / weight_total if weight_total > 0 else 0.0)

    def classification(self) -> str:
        """Maps session_integrity_score to CLEAN/WATCH/FLAG/ESCALATE."""
        score = self.session_integrity_score()
        for label, (lo, hi) in INTEGRITY_THRESHOLDS.items():
            if lo <= score <= hi:
                return label
        return "ESCALATE" if score > 75 else "CLEAN"

    def duration_str(self) -> str:
        """Human-readable session duration."""
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{minutes}m {seconds}s"

    def to_dict(self) -> dict:
        """Full serialisable session dump."""
        return {
            "candidate_name": self.candidate_name,
            "experience_tier": self.experience_tier,
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "duration": self.duration_str(),
            "session_integrity_score": round(self.session_integrity_score(), 2),
            "classification": self.classification(),
            "turns": [asdict(t) for t in self.turns],
            "mia_events": [asdict(e) for e in self.mia_events],
            "vsa_events": [asdict(e) for e in self.vsa_events],
            "integrity_scores": [round(s, 2) for s in self.integrity_scores],
            "snapshot_paths": self.snapshot_paths,
        }

    def save_json(self, directory: Optional[str] = None) -> str:
        """Write session data to JSON file. Returns file path."""
        out_dir = directory or REPORT_DIR
        os.makedirs(out_dir, exist_ok=True)
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"session_{timestamp}.json"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        return filepath
