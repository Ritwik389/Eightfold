"""
SENTINEL — Integrity Annex Generator

Builds the formal Integrity Annex PDF section using fpdf2.
Helvetica throughout. No emojis. No colour beyond black and
dark grey (#333333). Formal evidentiary document format.
"""

import os
import logging
from datetime import datetime
from typing import Optional

from sentinel.config import SNAPSHOT_DIR, REPORT_DIR
from sentinel.session_log import SessionLog, MIAEvent, VSAEvent

logger = logging.getLogger("sentinel.annex")

# ════════════════════════════════════════════════════════════
# COLOUR CONSTANTS
# ════════════════════════════════════════════════════════════
BLACK = (0, 0, 0)
DARK_GREY = (51, 51, 51)  # #333333
LIGHT_GREY = (200, 200, 200)

DISCLAIMER_TEXT = (
    "This annex is produced by an automated integrity monitoring system. "
    "All signals are probabilistic. No automated system should serve as the "
    "sole basis for a hiring decision. Human review is mandatory before any "
    "adverse action is taken."
)


def _generate_heatmap(audio_data: list, output_path: str) -> bool:
    """
    Generate an audio energy heatmap PNG.

    Args:
        audio_data: List of (timestamp_seconds, energy, is_speech).
        output_path: Where to save the PNG.

    Returns:
        True if heatmap generated successfully.
    """
    if not audio_data:
        return False

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        timestamps = [d[0] for d in audio_data]
        energies = [d[1] for d in audio_data]
        speech_flags = [d[2] for d in audio_data]

        fig, ax = plt.subplots(figsize=(12, 3))
        colors = ["#1a1aff" if not s else "#ff3333" for s in speech_flags]
        ax.bar(timestamps, energies, width=0.05, color=colors, alpha=0.7)
        ax.set_xlabel("Time (seconds)", fontsize=9)
        ax.set_ylabel("Energy Amplitude", fontsize=9)
        ax.set_title("Audio Energy Heatmap", fontsize=11)
        ax.set_facecolor("#f5f5f5")
        fig.tight_layout()
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return True

    except Exception as e:
        logger.warning(f"Heatmap generation failed: {e}")
        return False


class AnnexGenerator:
    """
    Generates the SENTINEL Integrity Annex PDF.
    Uses fpdf2 (FPDF2) and Pillow for embedded snapshots.
    """

    def __init__(self):
        self._vlm = None

    def _get_vlm(self):
        """Lazy-load VLM describer."""
        if self._vlm is None:
            from sentinel.report.vlm_describer import VLMDescriber
            self._vlm = VLMDescriber()
        return self._vlm

    def build_annex(
        self,
        session_log: SessionLog,
        audio_data: Optional[list] = None,
        vsa_report_data: Optional[dict] = None,
    ) -> bytes:
        """
        Build the complete Integrity Annex PDF.

        Args:
            session_log: Complete session log.
            audio_data: Optional heatmap data from AudioMonitor.
            vsa_report_data: Optional VSA report data.

        Returns:
            PDF as bytes.
        """
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)

        vlm = self._get_vlm()
        session_data = session_log.to_dict()

        # ─── 1. COVER LINE ───────────────────────────────────
        pdf.add_page()
        self._render_cover(pdf, session_log)

        # ─── 2. EXECUTIVE INTEGRITY SUMMARY ──────────────────
        self._render_executive_summary(pdf, vlm, session_data)

        # ─── 3. LEXICAL CONSISTENCY ANALYSIS ─────────────────
        self._render_lca_section(pdf, vlm, session_log)

        # ─── 4. SEMANTIC DRIFT ANALYSIS ──────────────────────
        self._render_sda_section(pdf, vlm, session_log)

        # ─── 5. AI GENERATION SIGNALS ────────────────────────
        self._render_aiga_section(pdf, vlm, session_log)

        # ─── 6. VOICE SIGNATURE ANALYSIS ─────────────────────
        if vsa_report_data and vsa_report_data.get("enrollment_complete"):
            self._render_vsa_section(pdf, vlm, vsa_report_data)

        # ─── 7. MULTIMODAL EVENT LOG ─────────────────────────
        self._render_mia_events(pdf, vlm, session_log)

        # ─── 8. AUDIO-LIP SYNC HEATMAP ──────────────────────
        self._render_heatmap(pdf, vlm, audio_data)

        # ─── 9. INTEGRITY SCORE TIMELINE ─────────────────────
        self._render_score_timeline(pdf, session_log)

        # ─── 10. RECRUITER GUIDANCE ──────────────────────────
        self._render_recruiter_guidance(pdf, vlm, session_data)

        # ─── 11. DISCLAIMER ─────────────────────────────────
        self._render_disclaimer(pdf)

        return pdf.output()

    # ══════════════════════════════════════════════════════
    # SECTION RENDERERS
    # ══════════════════════════════════════════════════════

    def _render_cover(self, pdf, session_log: SessionLog):
        """Render the cover line section."""
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*BLACK)
        pdf.cell(0, 12, "SENTINEL INTEGRITY ANNEX", ln=True, align="C")
        pdf.ln(6)

        pdf.set_font("Helvetica", "", 10)
        data = [
            ("Candidate", session_log.candidate_name),
            ("Date", session_log.start_time.strftime("%Y-%m-%d %H:%M:%S")),
            ("Duration", session_log.duration_str()),
            ("Integrity Score", f"{session_log.session_integrity_score():.1f} / 100"),
            ("Classification", session_log.classification()),
        ]
        for label, value in data:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(40, 7, f"{label}:", ln=False)
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, str(value), ln=True)

        pdf.ln(4)
        pdf.set_draw_color(*LIGHT_GREY)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    def _section_header(self, pdf, title: str):
        """Render a section header."""
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*DARK_GREY)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_draw_color(*LIGHT_GREY)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(*BLACK)
        pdf.set_font("Helvetica", "", 10)

    def _body_text(self, pdf, text: str):
        """Render body text with safe encoding."""
        safe = text.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe)
        pdf.ln(2)

    def _render_executive_summary(self, pdf, vlm, session_data):
        """Section 2: Executive Integrity Summary."""
        self._section_header(pdf, "EXECUTIVE INTEGRITY SUMMARY")
        try:
            summary = vlm.generate_executive_summary(session_data)
        except Exception:
            summary = "Executive summary generation unavailable."
        self._body_text(pdf, summary)

    def _render_lca_section(self, pdf, vlm, session_log: SessionLog):
        """Section 3: Lexical Consistency Analysis."""
        self._section_header(pdf, "LEXICAL CONSISTENCY ANALYSIS")

        if not session_log.turns:
            self._body_text(pdf, "No turns recorded for lexical analysis.")
            return

        # FK baseline and range
        fk_values = [
            t.lca_result.get("fk_grade", 0)
            for t in session_log.turns if t.lca_result
        ]
        if fk_values:
            pdf.set_font("Helvetica", "", 9)
            baseline = sum(fk_values) / len(fk_values)
            fk_min = min(fk_values)
            fk_max = max(fk_values)
            pdf.cell(0, 5, f"FK Baseline: {baseline:.1f} | Range: {fk_min:.1f} - {fk_max:.1f}", ln=True)
            pdf.ln(2)

        # Anomalous turns
        anomalous = [
            t for t in session_log.turns
            if t.lca_result.get("signal") in ("RED", "AMBER")
        ]
        if anomalous:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, f"Anomalous Turns: {len(anomalous)}", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for t in anomalous:
                pdf.cell(
                    0, 5,
                    f"  Turn {t.turn_index}: FK {t.lca_result.get('fk_grade', 0):.1f} "
                    f"[{t.lca_result.get('signal', '?')}] - {t.lca_result.get('note', '')}",
                    ln=True,
                )
            pdf.ln(2)

        # Assessment
        try:
            lca_data = {
                "fk_values": fk_values,
                "anomalous_count": len(anomalous),
                "turns": len(session_log.turns),
            }
            assessment = vlm.generate_section_assessment("Lexical Consistency", lca_data)
        except Exception:
            assessment = "Assessment generation unavailable."
        self._body_text(pdf, assessment)

    def _render_sda_section(self, pdf, vlm, session_log: SessionLog):
        """Section 4: Semantic Drift Analysis."""
        self._section_header(pdf, "SEMANTIC DRIFT ANALYSIS")

        if not session_log.turns:
            self._body_text(pdf, "No turns recorded for semantic analysis.")
            return

        # Cosine profile table
        pdf.set_font("Helvetica", "B", 9)
        col_widths = [20, 50, 50, 60]
        headers = ["Turn", "Session Cosine", "Q-A Cosine", "Signal"]
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 6, h, border=1, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        trajectory_delta = 0.0
        for t in session_log.turns:
            sda = t.sda_result
            pdf.cell(col_widths[0], 5, str(t.turn_index), border=1, align="C")
            pdf.cell(col_widths[1], 5, f"{sda.get('cosine_to_session_mean', 0):.3f}", border=1, align="C")
            pdf.cell(col_widths[2], 5, f"{sda.get('q_to_a_cosine', 0):.3f}", border=1, align="C")
            pdf.cell(col_widths[3], 5, sda.get("signal", "GREEN"), border=1, align="C")
            pdf.ln()
            trajectory_delta = sda.get("trajectory_delta", 0)

        pdf.ln(2)
        pdf.cell(0, 5, f"Trajectory Delta: {trajectory_delta:.4f}", ln=True)
        pdf.ln(2)

        # Assessment
        try:
            sda_data = {
                "turns_count": len(session_log.turns),
                "trajectory_delta": trajectory_delta,
            }
            assessment = vlm.generate_section_assessment("Semantic Drift", sda_data)
        except Exception:
            assessment = "Assessment generation unavailable."
        self._body_text(pdf, assessment)

    def _render_aiga_section(self, pdf, vlm, session_log: SessionLog):
        """Section 5: AI Generation Signals."""
        self._section_header(pdf, "AI GENERATION SIGNALS")

        if not session_log.turns:
            self._body_text(pdf, "No turns recorded for AI generation analysis.")
            return

        flagged = [
            t for t in session_log.turns
            if t.aiga_result.get("signal") in ("RED", "AMBER")
        ]

        # Burstiness profile
        pdf.set_font("Helvetica", "", 9)
        for t in session_log.turns:
            aiga = t.aiga_result
            pdf.cell(
                0, 5,
                f"Turn {t.turn_index}: Burstiness={aiga.get('burstiness_score', 0):.3f} | "
                f"Hedge={aiga.get('hedge_ratio', 0):.4f} | "
                f"Anchor={'Yes' if aiga.get('temporal_anchor_found') else 'No'} | "
                f"[{aiga.get('signal', 'GREEN')}]",
                ln=True,
            )
        pdf.ln(2)

        if flagged:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, f"Flagged Turns: {len(flagged)}", ln=True)
            pdf.set_font("Helvetica", "", 9)
            for t in flagged:
                pdf.cell(0, 5, f"  Turn {t.turn_index}: {t.aiga_result.get('note', '')}", ln=True)
            pdf.ln(2)

        # Assessment
        try:
            aiga_data = {
                "flagged_count": len(flagged),
                "total_turns": len(session_log.turns),
            }
            assessment = vlm.generate_section_assessment("AI Generation Detection", aiga_data)
        except Exception:
            assessment = "Assessment generation unavailable."
        self._body_text(pdf, assessment)

    def _render_vsa_section(self, pdf, vlm, vsa_data: dict):
        """Section 6: Voice Signature Analysis."""
        self._section_header(pdf, "VOICE SIGNATURE ANALYSIS")

        pdf.set_font("Helvetica", "", 9)
        status = "Complete" if vsa_data.get("enrollment_complete") else "Incomplete"
        pdf.cell(0, 5, f"Enrollment Status: {status}", ln=True)
        pdf.cell(
            0, 5,
            f"Baseline Built From: {vsa_data.get('baseline_segments_count', 0)} segments "
            f"across turns 1-{vsa_data.get('enrollment_turns', 3)}",
            ln=True,
        )
        pdf.cell(0, 5, f"Turns Analysed: {vsa_data.get('turns_analysed', 0)}", ln=True)

        if vsa_data.get("uses_mfcc_fallback"):
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.cell(
                0, 5,
                "Note: d-vector encoder unavailable. MFCC fallback active. "
                "Confidence of voice analysis is reduced.",
                ln=True,
            )
            pdf.set_font("Helvetica", "", 9)

        pdf.ln(4)

        # Per-turn distance table
        distances = vsa_data.get("turn_distances", [])
        if distances:
            pdf.set_font("Helvetica", "B", 9)
            col_widths = [20, 45, 40, 45]
            headers = ["Turn", "Mean Distance", "Signal", "Anomaly Type"]
            for i, h in enumerate(headers):
                pdf.cell(col_widths[i], 6, h, border=1, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 9)
            for idx, dist in enumerate(distances):
                turn_num = idx + vsa_data.get("enrollment_turns", 3) + 1
                if dist >= 0.30:
                    sig = "RED"
                elif dist >= 0.18:
                    sig = "AMBER"
                else:
                    sig = "GREEN"
                pdf.cell(col_widths[0], 5, str(turn_num), border=1, align="C")
                pdf.cell(col_widths[1], 5, f"{dist:.4f}", border=1, align="C")
                pdf.cell(col_widths[2], 5, sig, border=1, align="C")
                pdf.cell(col_widths[3], 5, "-" if sig == "GREEN" else "See events", border=1, align="C")
                pdf.ln()

        pdf.ln(4)

        # Flagged voice events
        events = vsa_data.get("anomaly_events", [])
        if events:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, "FLAGGED VOICE EVENTS", ln=True)
            pdf.ln(2)

            for evt in events:
                y_start = pdf.get_y()
                pdf.set_draw_color(*DARK_GREY)
                pdf.set_font("Helvetica", "", 9)

                pdf.cell(0, 5, f"Anomaly Type:    {evt.get('anomaly_type', 'UNKNOWN')}", ln=True)
                pdf.cell(0, 5, f"Timestamp:       {evt.get('timestamp_str', '')}", ln=True)
                pdf.cell(
                    0, 5,
                    f"Segment:         {evt.get('segment_start_ms', 0)}ms - "
                    f"{evt.get('segment_end_ms', 0)}ms",
                    ln=True,
                )
                pdf.cell(0, 5, f"Cosine Distance: {evt.get('cosine_distance', 0):.4f}", ln=True)
                pdf.cell(0, 5, f"Signal:          {evt.get('signal', '')}", ln=True)

                # Recruiter note
                try:
                    note = vlm.generate_recruiter_note(evt)
                    pdf.cell(0, 5, f"Recruiter Note:  {note[:100]}", ln=True)
                except Exception:
                    pass

                y_end = pdf.get_y()
                pdf.rect(8, y_start - 1, 194, y_end - y_start + 3)
                pdf.ln(4)

        # Assessment
        try:
            assessment = vlm.generate_section_assessment("Voice Signature", vsa_data)
        except Exception:
            assessment = "Assessment generation unavailable."
        self._body_text(pdf, assessment)

    def _render_mia_events(self, pdf, vlm, session_log: SessionLog):
        """Section 7: Multimodal Event Log."""
        self._section_header(pdf, "MULTIMODAL EVENT LOG")

        events = session_log.mia_events
        if not events:
            self._body_text(pdf, "No multimodal integrity events recorded.")
            return

        for event in events:
            y_start = pdf.get_y()

            # Check page space
            if pdf.get_y() > 230:
                pdf.add_page()
                y_start = pdf.get_y()

            pdf.set_draw_color(*DARK_GREY)
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, f"Event Type: {event.event_type}", ln=True)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, f"Timestamp: {event.timestamp_str}", ln=True)
            pdf.cell(0, 5, f"Confidence: {event.confidence:.2f}", ln=True)

            # VLM description
            if event.snapshot_path and os.path.exists(event.snapshot_path):
                try:
                    desc = vlm.describe_snapshot(
                        event.snapshot_path, event.event_type, event.timestamp_str
                    )
                    pdf.multi_cell(0, 5, f"VLM Description: {desc[:200]}")
                except Exception:
                    pdf.cell(0, 5, "VLM Description: unavailable", ln=True)

            # Recruiter note
            try:
                note = vlm.generate_recruiter_note({
                    "event_type": event.event_type,
                    "confidence": event.confidence,
                    "note": event.note,
                })
                pdf.multi_cell(0, 5, f"Recruiter Note: {note[:150]}")
            except Exception:
                pass

            # Embedded snapshot
            if event.snapshot_path and os.path.exists(event.snapshot_path):
                try:
                    pdf.image(event.snapshot_path, x=10, w=120)
                except Exception:
                    pass

            y_end = pdf.get_y()
            pdf.rect(8, y_start - 1, 194, y_end - y_start + 3)
            pdf.ln(4)

    def _render_heatmap(self, pdf, vlm, audio_data):
        """Section 8: Audio-Lip Sync Heatmap."""
        self._section_header(pdf, "AUDIO-LIP SYNC HEATMAP")

        if not audio_data:
            self._body_text(pdf, "No audio data available for heatmap generation.")
            return

        os.makedirs(SNAPSHOT_DIR, exist_ok=True)
        heatmap_path = os.path.join(SNAPSHOT_DIR, "heatmap.png")

        if _generate_heatmap(audio_data, heatmap_path):
            try:
                pdf.image(heatmap_path, x=10, w=190)
                pdf.ln(4)
            except Exception:
                self._body_text(pdf, "Heatmap image could not be embedded.")

            # VLM description
            try:
                desc = vlm.describe_audio_heatmap(heatmap_path)
                self._body_text(pdf, desc)
            except Exception:
                pass
        else:
            self._body_text(pdf, "Heatmap generation failed.")

    def _render_score_timeline(self, pdf, session_log: SessionLog):
        """Section 9: Integrity Score Timeline."""
        self._section_header(pdf, "INTEGRITY SCORE TIMELINE")

        if not session_log.turns:
            self._body_text(pdf, "No turns recorded.")
            return

        pdf.set_font("Helvetica", "B", 9)
        col_widths = [25, 55, 55]
        for i, h in enumerate(["Turn", "Score", "Classification"]):
            pdf.cell(col_widths[i], 6, h, border=1, align="C")
        pdf.ln()

        pdf.set_font("Helvetica", "", 9)
        for t in session_log.turns:
            pdf.cell(col_widths[0], 5, str(t.turn_index), border=1, align="C")
            pdf.cell(col_widths[1], 5, f"{t.integrity_score:.1f}", border=1, align="C")
            pdf.cell(col_widths[2], 5, t.classification, border=1, align="C")
            pdf.ln()

        # Final row
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_widths[0], 6, "AVG", border=1, align="C")
        pdf.cell(col_widths[1], 6, f"{session_log.session_integrity_score():.1f}", border=1, align="C")
        pdf.cell(col_widths[2], 6, session_log.classification(), border=1, align="C")
        pdf.ln(6)

    def _render_recruiter_guidance(self, pdf, vlm, session_data):
        """Section 10: Recruiter Guidance."""
        self._section_header(pdf, "RECRUITER GUIDANCE")

        try:
            guidance = vlm.generate_recruiter_guidance(session_data)
            self._body_text(pdf, guidance)
        except Exception:
            self._body_text(pdf, "Recruiter guidance generation unavailable.")

    def _render_disclaimer(self, pdf):
        """Section 11: Disclaimer."""
        pdf.ln(8)
        pdf.set_draw_color(*LIGHT_GREY)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(100, 100, 100)
        safe_text = DISCLAIMER_TEXT.encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 4, safe_text)
