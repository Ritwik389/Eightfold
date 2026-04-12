"""
SENTINEL Configuration — All constants and thresholds in one place.
No magic numbers anywhere else in the codebase.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ════════════════════════════════════════════════════════════
# API KEYS
# ════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ════════════════════════════════════════════════════════════
# EXPERIENCE TIER CALIBRATION
# ════════════════════════════════════════════════════════════
EXPERIENCE_TIERS = {
    "Fresher":         {"fk_range": (6, 10),  "threshold_multiplier": 1.5},
    "Junior":          {"fk_range": (8, 11),  "threshold_multiplier": 1.2},
    "Mid-level":       {"fk_range": (10, 13), "threshold_multiplier": 1.0},
    "Senior":          {"fk_range": (11, 14), "threshold_multiplier": 0.85},
    "Principal/Staff": {"fk_range": (12, 15), "threshold_multiplier": 0.75},
}

# ════════════════════════════════════════════════════════════
# INTEGRITY CLASSIFICATION BANDS
# ════════════════════════════════════════════════════════════
INTEGRITY_THRESHOLDS = {
    "CLEAN":    (0, 25),
    "WATCH":    (26, 50),
    "FLAG":     (51, 75),
    "ESCALATE": (76, 100),
}

# ════════════════════════════════════════════════════════════
# SCORE WEIGHTS PER AGENT PER SIGNAL
# ════════════════════════════════════════════════════════════
SCORE_WEIGHTS = {
    "LCA":  {"RED": 25, "AMBER": 10, "GREEN": 0},
    "SDA":  {"RED": 25, "AMBER": 10, "GREEN": 0},
    "AIGA": {"RED": 20, "AMBER": 8,  "GREEN": 0},
    "MIA":  {"RED": 15, "AMBER": 5,  "GREEN": 0},
    "VSA":  {"RED": 30, "AMBER": 12, "GREEN": 0},
}

# ════════════════════════════════════════════════════════════
# LATE SESSION WEIGHTING
# ════════════════════════════════════════════════════════════
LATE_SESSION_WEIGHT_MULTIPLIER = 1.5  # Applied to final third of turns

# ════════════════════════════════════════════════════════════
# SEMANTIC DRIFT AGENT THRESHOLDS
# ════════════════════════════════════════════════════════════
SDA_COSINE_THRESHOLDS = {
    "RED":   0.40,
    "AMBER": 0.55,
}

# ════════════════════════════════════════════════════════════
# AI GENERATION DETECTION AGENT THRESHOLDS
# ════════════════════════════════════════════════════════════
AIGA_BURSTINESS_RED   = 0.15   # Variance in sentence length; below = suspicious
AIGA_HEDGE_RATIO_RED  = 0.02   # Proportion of hedge tokens; below = suspicious

# ════════════════════════════════════════════════════════════
# MULTIMODAL INTEGRITY AGENT THRESHOLDS
# ════════════════════════════════════════════════════════════
MIA_GAZE_DRIFT_SECONDS     = 2.0
MIA_LIP_SYNC_TOLERANCE_MS  = 200
MIA_LIP_SYNC_MIN_GAP_MS    = 500
MIA_YOLO_CLASSES_OF_INTEREST = ["person", "cell phone", "laptop", "monitor", "earphone"]

# ════════════════════════════════════════════════════════════
# VOICE SIGNATURE AGENT THRESHOLDS
# ════════════════════════════════════════════════════════════
VSA_COSINE_THRESHOLDS = {
    "GREEN_MAX": 0.18,   # Below = same speaker
    "AMBER_MAX": 0.30,   # Between GREEN_MAX and this = AMBER
    # Above AMBER_MAX = RED
}
VSA_ENROLLMENT_TURNS = 3       # Number of turns for baseline enrollment
VSA_MFCC_FALLBACK_AMBER = 0.25
VSA_MFCC_FALLBACK_RED = 0.40
VSA_VOICE_DRIFT_THRESHOLD = 0.22  # Session-level drift detection

# ════════════════════════════════════════════════════════════
# COMPOSITE EVENT SCORING
# ════════════════════════════════════════════════════════════
VOICE_WITHOUT_LIP_MOVEMENT_BONUS = 20

# ════════════════════════════════════════════════════════════
# DIRECTORIES
# ════════════════════════════════════════════════════════════
SNAPSHOT_DIR = "snapshots"
REPORT_DIR   = "reports"

# ════════════════════════════════════════════════════════════
# GEMINI MODEL CONFIGURATION
# ════════════════════════════════════════════════════════════
GEMINI_MODEL = "gemini-2.5-pro"
GEMINI_MAX_RETRIES = 3
GEMINI_BACKOFF_BASE = 2  # Exponential backoff base in seconds
