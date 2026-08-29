# HireMind: AI-Powered Technical Interview Platform with SENTINEL Monitoring

![Status](https://img.shields.io/badge/status-production--ready-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Node.js](https://img.shields.io/badge/node-18+-green)
![License](https://img.shields.io/badge/license-proprietary-red)

**HireMind** is a professional, voice-first technical interview platform combining real-time multimodal monitoring, intelligent evaluation, and AI-powered fraud detection.

**SENTINEL** is the embedded integrity system that runs throughout the interview, analyzing candidates for authenticity and generating detailed fraud detection reports.

> **The candidate interview is voice-based (no typing), monitored with 6 parallel agents (SENTINEL), and evaluated with Groq LLaMA 3.3 70B.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    HireMind (app.py)                     │
│              Groq + LLaMA-3.3-70b-versatile             │
└────────────────────┬────────────────────────────────────┘
                     │ on_turn(question, response)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              SENTINEL Orchestrator                       │
│          (concurrent.futures ThreadPool)                 │
├──────┬──────┬──────┬──────┬──────┬──────────────────────┤
│ ECA  │ LCA  │ SDA  │ AIGA │ VSA  │  MIA (continuous)   │
│      │      │      │      │      │  ┌────────────────┐  │
│      │      │      │      │      │  │ VideoMonitor   │  │
│      │      │      │      │      │  │ AudioMonitor   │  │
│      │      │      │      │      │  └────────────────┘  │
└──────┴──────┴──────┴──────┴──────┴──────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Annex Generator (fpdf2)                    │
│           + Gemini 1.5 Pro VLM Describer                │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
              Integrity Annex PDF
```

---

## Sub-Agents

### 1. ECA — Experience Calibration Agent
Runs first at session start. Looks up the candidate's declared experience tier and returns calibrated thresholds (FK reading range, multiplier) that LCA and SDA use to adjust their sensitivity. Freshers get wider tolerances; senior candidates get stricter scrutiny.

### 2. LCA — Lexical Consistency Agent
Monitors **Flesch-Kincaid grade level** across turns. Detects sudden jumps in linguistic complexity that may indicate switching from genuine spoken responses to pasted/AI-generated content. Special rule: fresher baseline leaping to senior-level FK grade triggers immediate RED.

### 3. SDA — Semantic Drift Agent
Tracks **sentence embedding trajectory** using `paraphrase-MiniLM-L6-v2`. Flags:
- Session-mean cosine divergence
- Suspiciously high question-answer cosine (pasted definitions)
- First-third vs. last-third coherence shift (trajectory delta)

### 4. AIGA — AI Generation Detection Agent
Statistical analysis of response text for AI-generation fingerprints:
- **Burstiness**: Low variance in sentence lengths → uniform → suspicious
- **Hedge ratio**: Absence of human uncertainty markers ("I think", "maybe")
- **Temporal anchors**: No first-person past-tense project references
- **Structural perfection**: Enumerated lists in spoken responses

### 5. VSA — Voice Signature Agent
**Speaker verification** using d-vector embeddings (resemblyzer) with MFCC fallback. Enrolls a voiceprint baseline from the first 3 turns, then detects:
- Secondary speakers
- Whispered prompts
- Voice relay / earpiece assistance
- Gradual voice substitution (session-level drift)

### 6. MIA — Multimodal Integrity Agent
Continuous audio-visual correlation:
- **Gaze tracking**: MediaPipe iris landmarks, flags sustained off-screen gaze
- **Lip sync**: Correlates lip aperture with audio VAD — flags speech without lip movement
- **Object detection**: YOLOv8 detects secondary persons, phones, extra monitors
- **Composite events**: VSA RED + closed lips = `VOICE_WITHOUT_LIP_MOVEMENT` (highest confidence signal)

---

## Score Weights

| Agent | RED | AMBER | GREEN | ECA Multiplier |
|-------|-----|-------|-------|----------------|
| LCA   | 25  | 10    | 0     | Yes            |
| SDA   | 25  | 10    | 0     | Yes            |
| AIGA  | 20  | 8     | 0     | No             |
| MIA   | 15  | 5     | 0     | No             |
| VSA   | 30  | 12    | 0     | No (biometric) |

**Late session multiplier**: Final third of turns weighted 1.5x.

### Classification Bands

| Band      | Score Range |
|-----------|-------------|
| CLEAN     | 0 – 25      |
| WATCH     | 26 – 50     |
| FLAG      | 51 – 75     |
| ESCALATE  | 76 – 100    |

---

## Installation

```bash
# 1. Clone the repository
cd EightFold

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model
python -m spacy download en_core_web_sm

# 5. Set up your API keys
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### .env Setup

```
GEMINI_API_KEY=your_google_gemini_api_key_here
```

Get your key from: https://aistudio.google.com/app/apikey

---

## Running

### Run the Interview App

```bash
streamlit run app.py
```

SENTINEL activates automatically when you click "Start Interview". The experience tier dropdown appears in the sidebar alongside existing configuration.

### Run Synthetic Tests

```bash
python tests/synthetic_sessions.py
```

This runs two synthetic interview transcripts through the SENTINEL pipeline in text-only mode (no webcam/microphone required):

- **Session A** (Genuine Fresher): Heavy hedging, college-level FK, no structural perfection → Expected: `CLEAN` or `WATCH`
- **Session B** (Suspicious Senior): Turns 1–3 genuine, Turns 4–6 shift to enumerated lists, zero hedging, perfect structure → Expected: `FLAG` or `ESCALATE`

---

## File Structure

```
sentinel/
  __init__.py
  orchestrator.py          # Central coordination layer
  config.py                # All thresholds and constants
  session_log.py           # In-memory + disk session state
  agents/
    __init__.py
    eca.py                 # Experience Calibration Agent
    lca.py                 # Lexical Consistency Agent
    sda.py                 # Semantic Drift Agent
    aiga.py                # AI Generation Detection Agent
    mia.py                 # Multimodal Integrity Agent
    vsa.py                 # Voice Signature Agent
  report/
    __init__.py
    annex_generator.py     # Integrity Annex PDF builder
    vlm_describer.py       # Gemini Vision descriptions
  utils/
    __init__.py
    audio.py               # VAD, energy, turn buffering
    video.py               # OpenCV, MediaPipe, YOLO
    snapshot.py            # Frame capture utilities
tests/
  __init__.py
  synthetic_sessions.py    # Synthetic test runner
snapshots/                 # Auto-created, gitignored
reports/                   # PDF output directory
.env                       # API keys (not committed)
requirements.txt
```

---

## Report Sections

The Integrity Annex PDF contains:

1. **Cover Line** — Candidate info, score, classification
2. **Executive Integrity Summary** — Gemini-generated 2-3 sentence overview
3. **Lexical Consistency Analysis** — FK baseline, range, anomalous turns
4. **Semantic Drift Analysis** — Cosine profile table, trajectory delta
5. **AI Generation Signals** — Burstiness, hedge ratio, temporal anchors
6. **Voice Signature Analysis** — Enrollment status, per-turn distances, flagged events
7. **Multimodal Event Log** — Gaze drift, lip sync, object detection with VLM descriptions
8. **Audio-Lip Sync Heatmap** — Visual energy timeline with VLM analysis
9. **Integrity Score Timeline** — Per-turn scores and session average
10. **Recruiter Guidance** — 3 actionable bullet points from Gemini
11. **Disclaimer** — Mandatory human review notice

---

## Notes

- All sub-agents fail gracefully. Parse errors return GREEN with a note — never crash the interview.
- Video/audio monitors run as daemon threads and degrade gracefully if hardware is unavailable.
- Gemini API calls use exponential backoff with 3 retries.
- Session data is saved as JSON to `reports/session_[timestamp].json` for debugging.
- All timestamps in the report are ISO 8601 format.
# Eightfold
