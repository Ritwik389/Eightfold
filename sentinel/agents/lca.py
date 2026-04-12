"""
SENTINEL — Lexical Consistency Agent (LCA)

Monitors Flesch-Kincaid grade consistency across turns.
Detects sudden shifts in linguistic complexity that may indicate
external assistance or content switching.
"""

import statistics
from dataclasses import dataclass

try:
    import textstat
except ImportError:
    textstat = None

from sentinel.agents.eca import ECAResult
from sentinel.config import EXPERIENCE_TIERS


@dataclass
class LCAResult:
    """Output of the Lexical Consistency Agent."""
    signal: str               # GREEN | AMBER | RED
    fk_grade: float
    session_baseline_fk: float  # Mean of prior turns (0.0 if first turn)
    deviation: float            # Current - baseline
    note: str


class LexicalConsistencyAgent:
    """
    Monitors Flesch-Kincaid reading level across interview turns.
    Flags sudden jumps in complexity that diverge from the candidate's
    established baseline.
    """

    def __init__(self):
        self.fk_history: list[float] = []
        self.syllable_history: list[float] = []
        self.sentence_len_history: list[float] = []

    def analyse(self, response: str, eca_result: ECAResult) -> LCAResult:
        """
        Analyse a single response turn for lexical consistency.

        Args:
            response: The candidate's response text.
            eca_result: Calibration data from ECA.

        Returns:
            LCAResult with signal and analysis data.
        """
        try:
            if textstat is None:
                return LCAResult(
                    signal="GREEN",
                    fk_grade=0.0,
                    session_baseline_fk=0.0,
                    deviation=0.0,
                    note="textstat unavailable — insufficient signal.",
                )

            if not response or len(response.split()) < 5:
                return LCAResult(
                    signal="GREEN",
                    fk_grade=0.0,
                    session_baseline_fk=0.0,
                    deviation=0.0,
                    note="Response too short for lexical analysis.",
                )

            # Compute metrics for this turn
            fk_grade = textstat.flesch_kincaid_grade(response)
            avg_syllables = textstat.avg_syllables_per_word(response)

            # Session baseline (before adding current turn)
            session_baseline_fk = (
                statistics.mean(self.fk_history) if self.fk_history else 0.0
            )
            baseline_std = (
                statistics.stdev(self.fk_history)
                if len(self.fk_history) >= 2
                else 1.0
            )

            deviation = abs(fk_grade - session_baseline_fk) if self.fk_history else 0.0

            # Determine signal
            signal = "GREEN"
            note = ""
            multiplier = eca_result.threshold_multiplier

            if self.fk_history:
                adjusted_threshold = 1.5 * multiplier
                threshold_value = adjusted_threshold * max(baseline_std, 0.5)

                # Special rule: fresher baseline but senior-level current grade
                fresher_range = EXPERIENCE_TIERS["Fresher"]["fk_range"]
                if (session_baseline_fk <= fresher_range[1]
                        and fk_grade >= 12):
                    signal = "RED"
                    note = (
                        f"FK grade jumped from fresher baseline "
                        f"({session_baseline_fk:.1f}) to senior level "
                        f"({fk_grade:.1f}). Possible external assistance."
                    )
                elif deviation > 2.0 * multiplier * max(baseline_std, 0.5):
                    signal = "RED"
                    note = (
                        f"FK deviation ({deviation:.2f}) exceeds RED threshold. "
                        f"Baseline: {session_baseline_fk:.1f}, Current: {fk_grade:.1f}."
                    )
                elif deviation > threshold_value:
                    signal = "AMBER"
                    note = (
                        f"FK deviation ({deviation:.2f}) exceeds AMBER threshold. "
                        f"Baseline: {session_baseline_fk:.1f}, Current: {fk_grade:.1f}."
                    )
                else:
                    note = (
                        f"Lexical complexity consistent. "
                        f"FK: {fk_grade:.1f}, Baseline: {session_baseline_fk:.1f}."
                    )
            else:
                note = f"First turn — establishing baseline at FK {fk_grade:.1f}."

            # Update history
            self.fk_history.append(fk_grade)
            self.syllable_history.append(avg_syllables)

            return LCAResult(
                signal=signal,
                fk_grade=fk_grade,
                session_baseline_fk=session_baseline_fk,
                deviation=deviation,
                note=note,
            )

        except Exception as e:
            # Fail gracefully
            self.fk_history.append(0.0)
            return LCAResult(
                signal="GREEN",
                fk_grade=0.0,
                session_baseline_fk=0.0,
                deviation=0.0,
                note=f"parse error — insufficient signal. ({str(e)})",
            )
