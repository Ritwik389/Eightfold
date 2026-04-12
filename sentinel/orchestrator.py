"""
SENTINEL — Orchestrator

Central coordination layer. Instantiated once per session.
Runs sub-agents in parallel, aggregates signals, and produces
the final Integrity Annex PDF.
"""

import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional
from dataclasses import asdict

import numpy as np

from sentinel.config import (
    SCORE_WEIGHTS,
    INTEGRITY_THRESHOLDS,
    SNAPSHOT_DIR,
    REPORT_DIR,
    VOICE_WITHOUT_LIP_MOVEMENT_BONUS,
)
from sentinel.session_log import SessionLog, TurnRecord, MIAEvent
from sentinel.agents.eca import ExperienceCalibrationAgent, ECAResult
from sentinel.agents.lca import LexicalConsistencyAgent
from sentinel.agents.sda import SemanticDriftAgent
from sentinel.agents.aiga import AIGenerationDetectionAgent
from sentinel.agents.mia import MultimodalIntegrityAgent
from sentinel.agents.vsa import VoiceSignatureAgent
from sentinel.utils.video import VideoMonitor
from sentinel.utils.audio import AudioMonitor
from sentinel.report.annex_generator import AnnexGenerator

logger = logging.getLogger("sentinel.orchestrator")


def _classify_score(score: float) -> str:
    """Map a numeric score to CLEAN/WATCH/FLAG/ESCALATE."""
    for label, (lo, hi) in INTEGRITY_THRESHOLDS.items():
        if lo <= score <= hi:
            return label
    return "ESCALATE" if score > 75 else "CLEAN"


class SentinelOrchestrator:
    """
    Main SENTINEL controller. Instantiated once per interview session.
    """

    def __init__(self):
        # Session state
        self.session_log: Optional[SessionLog] = None
        self._turn_index: int = 0

        # Sub-agents
        self._eca = ExperienceCalibrationAgent()
        self._lca = LexicalConsistencyAgent()
        self._sda = SemanticDriftAgent()
        self._aiga = AIGenerationDetectionAgent()
        self._vsa = VoiceSignatureAgent()

        # Multimodal components
        self._video_monitor = VideoMonitor()
        self._audio_monitor = AudioMonitor()
        self._mia: Optional[MultimodalIntegrityAgent] = None

        # ECA result (set at session start)
        self._eca_result: Optional[ECAResult] = None

        # Thread pool for parallel agent execution
        self._executor = ThreadPoolExecutor(max_workers=5)

        # WebRTC mode flag
        self._webrtc_mode = False

    def enable_webrtc_mode(self):
        """
        Enable WebRTC mode: video/audio frames come from streamlit-webrtc
        callbacks instead of daemon threads.
        """
        self._webrtc_mode = True
        self._video_monitor.set_webrtc_mode(True)
        self._audio_monitor.set_webrtc_mode(True)

    @property
    def video_monitor(self) -> VideoMonitor:
        """Expose video monitor for webrtc callback wiring."""
        return self._video_monitor

    @property
    def audio_monitor(self) -> AudioMonitor:
        """Expose audio monitor for webrtc callback wiring."""
        return self._audio_monitor

    def on_session_start(
        self, candidate_name: str, experience_tier: str
    ) -> None:
        """
        Initialise a new SENTINEL monitoring session.

        Args:
            candidate_name: Name of the candidate.
            experience_tier: Declared experience level.
        """
        try:
            # Create directories
            os.makedirs(SNAPSHOT_DIR, exist_ok=True)
            os.makedirs(REPORT_DIR, exist_ok=True)

            # Initialise session log
            self.session_log = SessionLog(
                candidate_name=candidate_name,
                experience_tier=experience_tier,
            )
            self._turn_index = 0

            # Run ECA (first — sets thresholds for others)
            self._eca_result = self._eca.analyse(experience_tier)
            logger.info(
                f"SENTINEL session started for '{candidate_name}' "
                f"({experience_tier}). ECA: {self._eca_result.note}"
            )

            # Start multimodal monitors
            video_ok = self._video_monitor.start(
                on_gaze_drift=self._on_gaze_drift,
                on_object_detected=self._on_object_detected,
            )
            audio_ok = self._audio_monitor.start()

            # Initialise MIA with monitors
            self._mia = MultimodalIntegrityAgent(
                self._video_monitor, self._audio_monitor
            )

            # Wire VSA snapshot callback
            if video_ok:
                self._vsa.set_snapshot_callback(self._video_monitor.snapshot)

            if video_ok:
                logger.info("Video monitoring active.")
            else:
                logger.info("Video monitoring unavailable — text-only mode.")

            if audio_ok:
                logger.info("Audio monitoring active.")
                self._audio_monitor.start_turn_recording()
            else:
                logger.info("Audio monitoring unavailable — text-only mode.")

        except Exception as e:
            logger.error(f"Session start failed: {e}")
            # Ensure we have a minimal session log even on failure
            if self.session_log is None:
                self.session_log = SessionLog(
                    candidate_name=candidate_name,
                    experience_tier=experience_tier,
                )
            if self._eca_result is None:
                self._eca_result = self._eca.analyse("Mid-level")

    def on_turn(self, question: str, response: str) -> dict:
        """
        Process a single interview turn through all sub-agents.

        Args:
            question: The interview question.
            response: The candidate's response.

        Returns:
            Dict with turn integrity data (for internal logging only).
        """
        self._turn_index += 1
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Collect turn audio from buffer
        turn_audio = np.array([], dtype=np.float32)
        if self._audio_monitor.is_available:
            turn_audio = self._audio_monitor.stop_turn_recording()
            # Start recording for next turn
            self._audio_monitor.start_turn_recording()

        # Run text-based agents concurrently
        futures = {}
        futures["lca"] = self._executor.submit(
            self._lca.analyse, response, self._eca_result
        )
        futures["sda"] = self._executor.submit(
            self._sda.analyse, question, response, self._eca_result
        )
        futures["aiga"] = self._executor.submit(
            self._aiga.analyse, response
        )

        # Run VSA if audio is available
        if len(turn_audio) > 0:
            futures["vsa"] = self._executor.submit(
                self._vsa.analyse_turn_audio, turn_audio
            )

        # Collect results
        lca_result = None
        sda_result = None
        aiga_result = None
        vsa_result = {"signal": "GREEN", "events": [], "mean_distance": 0.0}

        for name, future in futures.items():
            try:
                result = future.result(timeout=30)
                if name == "lca":
                    lca_result = result
                elif name == "sda":
                    sda_result = result
                elif name == "aiga":
                    aiga_result = result
                elif name == "vsa":
                    vsa_result = result
            except Exception as e:
                logger.error(f"Agent {name} failed: {e}")

        # Safe defaults
        if lca_result is None:
            from sentinel.agents.lca import LCAResult
            lca_result = LCAResult("GREEN", 0, 0, 0, "Agent unavailable.")
        if sda_result is None:
            from sentinel.agents.sda import SDAResult
            sda_result = SDAResult("GREEN", 0, 0, 0, "Agent unavailable.")
        if aiga_result is None:
            from sentinel.agents.aiga import AIGAResult
            aiga_result = AIGAResult("GREEN", 1.0, 0, False, "Agent unavailable.")

        # Check MIA lip sync
        mia_signal = "GREEN"
        if self._mia:
            lip_event = self._mia.check_lip_sync()
            if lip_event and self.session_log:
                self.session_log.add_mia_event(lip_event)

            # Check for composite VSA+MIA event
            if vsa_result.get("signal") == "RED":
                composite = self._mia.check_composite_vsa_event(
                    vsa_result["signal"],
                    vsa_result.get("mean_distance", 0),
                )
                if composite and self.session_log:
                    self.session_log.add_mia_event(composite)

            mia_signal = self._mia.get_signal()

        # Compute turn integrity score
        multiplier = self._eca_result.threshold_multiplier if self._eca_result else 1.0

        raw_score = 0.0
        # LCA + SDA: apply ECA multiplier
        raw_score += SCORE_WEIGHTS["LCA"].get(lca_result.signal, 0) * multiplier
        raw_score += SCORE_WEIGHTS["SDA"].get(sda_result.signal, 0) * multiplier
        # AIGA: no multiplier adjustment
        raw_score += SCORE_WEIGHTS["AIGA"].get(aiga_result.signal, 0)
        # MIA: scored from events
        raw_score += SCORE_WEIGHTS["MIA"].get(mia_signal, 0)
        # VSA: no ECA multiplier (biometric)
        raw_score += SCORE_WEIGHTS["VSA"].get(vsa_result.get("signal", "GREEN"), 0)

        # Add composite event bonus
        if self._mia:
            for evt in self._mia.events:
                if evt.event_type == "VOICE_WITHOUT_LIP_MOVEMENT":
                    raw_score += VOICE_WITHOUT_LIP_MOVEMENT_BONUS

        integrity_score = min(100.0, raw_score)
        classification = _classify_score(integrity_score)

        # Build turn record
        turn_record = TurnRecord(
            turn_index=self._turn_index,
            question=question,
            response=response,
            timestamp=timestamp,
            lca_result=asdict(lca_result),
            sda_result=asdict(sda_result),
            eca_result=asdict(self._eca_result) if self._eca_result else {},
            aiga_result=asdict(aiga_result),
            vsa_result=vsa_result,
            integrity_score=integrity_score,
            classification=classification,
        )

        # Add VSA events to session log
        if self.session_log:
            for evt in vsa_result.get("events", []):
                if hasattr(evt, "timestamp_str"):
                    self.session_log.add_vsa_event(evt)

            self.session_log.add_turn(turn_record)

        logger.info(
            f"Turn {self._turn_index}: score={integrity_score:.1f} "
            f"class={classification} "
            f"LCA={lca_result.signal} SDA={sda_result.signal} "
            f"AIGA={aiga_result.signal} MIA={mia_signal} "
            f"VSA={vsa_result.get('signal', 'GREEN')}"
        )

        return {
            "turn_index": self._turn_index,
            "integrity_score": integrity_score,
            "classification": classification,
            "lca_signal": lca_result.signal,
            "sda_signal": sda_result.signal,
            "aiga_signal": aiga_result.signal,
            "mia_signal": mia_signal,
            "vsa_signal": vsa_result.get("signal", "GREEN"),
        }

    def on_session_end(self) -> str:
        """
        End the SENTINEL monitoring session.
        Generates the Integrity Annex PDF and returns the file path.

        Returns:
            Path to the final PDF report.
        """
        try:
            # Stop monitors
            self._video_monitor.stop()
            self._audio_monitor.stop()

            # Record end time
            if self.session_log:
                self.session_log.end_time = datetime.now()

            # VSA session-level drift check
            drift_event = self._vsa.session_drift_check()
            if drift_event and self.session_log:
                self.session_log.add_vsa_event(drift_event)

            # Get audio heatmap data
            audio_data = self._audio_monitor.heatmap_data()

            # Get VSA report data
            vsa_report_data = self._vsa.get_report_data()

            # Save session JSON
            if self.session_log:
                json_path = self.session_log.save_json()
                logger.info(f"Session JSON saved to {json_path}")

            # Generate annex PDF
            annex_gen = AnnexGenerator()
            pdf_bytes = annex_gen.build_annex(
                session_log=self.session_log,
                audio_data=audio_data if audio_data else None,
                vsa_report_data=vsa_report_data,
            )

            # Save PDF
            os.makedirs(REPORT_DIR, exist_ok=True)
            candidate = (
                self.session_log.candidate_name.replace(" ", "_")
                if self.session_log
                else "Unknown"
            )
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"HireMind_Report_{candidate}_{timestamp}.pdf"
            pdf_path = os.path.join(REPORT_DIR, pdf_filename)

            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            logger.info(
                f"SENTINEL report generated: {pdf_path} | "
                f"Score: {self.session_log.session_integrity_score():.1f} | "
                f"Classification: {self.session_log.classification()}"
            )

            # Shutdown executor
            self._executor.shutdown(wait=False)

            return pdf_path

        except Exception as e:
            logger.error(f"Session end failed: {e}")
            # Return a fallback path
            fallback = os.path.join(REPORT_DIR, "sentinel_error.pdf")
            try:
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Helvetica", size=12)
                pdf.cell(0, 10, "SENTINEL: Report generation failed.", ln=True)
                pdf.cell(0, 10, f"Error: {str(e)}", ln=True)
                os.makedirs(REPORT_DIR, exist_ok=True)
                pdf.output(fallback)
            except Exception:
                pass
            return fallback

    # ═══════════════════════════════════════════════════
    # EVENT CALLBACKS (from VideoMonitor)
    # ═══════════════════════════════════════════════════

    def _on_gaze_drift(self, event) -> None:
        """Handle gaze drift event from VideoMonitor."""
        if self._mia:
            self._mia.on_gaze_drift(event)
            if self.session_log:
                for mia_evt in self._mia.events:
                    if mia_evt not in self.session_log.mia_events:
                        self.session_log.add_mia_event(mia_evt)

    def _on_object_detected(self, event) -> None:
        """Handle object detection event from VideoMonitor."""
        if self._mia:
            self._mia.on_object_detected(event)
            if self.session_log:
                for mia_evt in self._mia.events:
                    if mia_evt not in self.session_log.mia_events:
                        self.session_log.add_mia_event(mia_evt)
