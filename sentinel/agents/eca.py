"""
SENTINEL — Experience Calibration Agent (ECA)

Run first at session start — sets thresholds for LCA and SDA.
This is a lookup table with calibrated constants, no ML required.
"""

from dataclasses import dataclass
from sentinel.config import EXPERIENCE_TIERS


@dataclass
class ECAResult:
    """Output of the Experience Calibration Agent."""
    tier: str
    threshold_multiplier: float
    adjusted_fk_range: tuple
    note: str


class ExperienceCalibrationAgent:
    """
    Calibrates thresholds based on the candidate's declared experience tier.
    Must be run first — its output is passed to LCA and SDA.
    """

    def analyse(self, experience_tier: str) -> ECAResult:
        """
        Look up the experience tier and return calibration parameters.

        Args:
            experience_tier: One of the keys in EXPERIENCE_TIERS.

        Returns:
            ECAResult with tier-specific thresholds.
        """
        try:
            tier_data = EXPERIENCE_TIERS.get(experience_tier)
            if tier_data is None:
                # Default to Mid-level if tier is unrecognised
                tier_data = EXPERIENCE_TIERS["Mid-level"]
                return ECAResult(
                    tier="Mid-level",
                    threshold_multiplier=tier_data["threshold_multiplier"],
                    adjusted_fk_range=tier_data["fk_range"],
                    note=f"Unrecognised tier '{experience_tier}' — defaulting to Mid-level.",
                )

            return ECAResult(
                tier=experience_tier,
                threshold_multiplier=tier_data["threshold_multiplier"],
                adjusted_fk_range=tier_data["fk_range"],
                note=f"Calibrated for {experience_tier} tier. "
                     f"FK range {tier_data['fk_range']}, "
                     f"multiplier {tier_data['threshold_multiplier']}.",
            )
        except Exception as e:
            # Fail gracefully — return safe defaults
            mid = EXPERIENCE_TIERS["Mid-level"]
            return ECAResult(
                tier="Mid-level",
                threshold_multiplier=mid["threshold_multiplier"],
                adjusted_fk_range=mid["fk_range"],
                note=f"ECA error: {str(e)} — defaulting to Mid-level.",
            )
