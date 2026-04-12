# ProctorSense AI — Real-Time OA Anomaly Detection
## APOGEE 2026 · Track C Hackathon

---

## Architecture

```
Browser (Frontend)                      Python Backend (Flask)
─────────────────                      ─────────────────────
MediaPipe FaceMesh          ──POST──▶  /api/face
  468 landmarks + iris                   → gaze_x, gaze_y, neck_angle
  real-time overlay canvas               → blink_rate, face_confidence

Web Audio API (VAD)         ──POST──▶  /api/voice
  16kHz mono RMS analysis               → energy, is_speech, duration
  speech segment detection

Paste/Keystroke detector    ──POST──▶  /api/text
  paste event + text content            → paste, burst, tab_switch
  typing velocity (chars/ms)            → text similarity scoring

Canvas screenshot capture   ──POST──▶  /api/screenshot
  annotated video frame PNG             → saved to /screenshots/

EventSource (SSE)           ◀──PUSH──  /api/stream
  receives: state, flag,                ← IsolationForest scores
            screenshot events           ← anomaly flags
                                        ← score updates (every 2s)
```

---

## Anomaly Detection — What's Real

### 1. Face (MediaPipe)
- **Iris tracking** (landmarks 468-477): Computes real gaze vector from iris position relative to eye corners
- **Neck angle**: Computed from cheek landmark tilt (landmark 234 vs 454)
- **Blink detection**: Eye Aspect Ratio (EAR) from eye landmarks
- **Gaze deviation**: Flags when √(gaze_x² + gaze_y²) > 0.35
- **Head tilt**: Flags when neck angle > 20°

### 2. Voice (Web Audio API)
- **RMS energy**: `√(Σx²/N)` over 512-sample FFT window at 16kHz
- **State machine VAD**: 3 consecutive frames above threshold → speech ON; 8 below → speech OFF
- **Segment logging**: Duration, event count sent to backend
- **Isolation Forest scoring**: Duration × energy boosts IF feature vector

### 3. Text (Paste + Velocity)
- **Paste events**: `onpaste` event fires → backend gets full text + length
- **Burst detection**: >20 chars in <300ms → velocity anomaly
- **N-gram similarity**: Compares pasted text against fingerprints of known LeetCode solutions
- **Tab switching**: `visibilitychange` API detects when candidate leaves the window
- **Scoring**: paste_count + similarity + velocity all fed to IF model

### 4. Isolation Forest (sklearn)
- **Features** (12-dimensional):
  ```
  gaze_x, gaze_y, neck_angle/45, (blink_rate-15)/10,
  1-face_confidence, voice_energy, voice_is_speech,
  voice_duration/10, paste_count/5, type_velocity/50,
  answer_similarity, tab_switches/5
  ```
- **Rolling window**: 200 samples, scaler fitted + IF fitted on each update
- **Contamination**: 0.08 (8% of samples assumed anomalous)
- **Score mapping**: `max(0, (0.3 - raw_score) × 200)` → 0–100 scale
- **Weighted overall**: eye(20%) + neck(10%) + voice(20%) + IF(25%) + paste(15%) + velocity(10%)

### 5. Screenshots
- Frontend captures annotated video frame via `canvas.toDataURL('image/png')`
- Timestamp + flag type overlaid on frame in orange
- Sent as base64 to `/api/screenshot` → saved as PNG in `./screenshots/`
- Served back to frontend for evidence strip and report modal

---

## Setup

### Requirements
```
Python 3.9+
Flask 3.x       (pip install flask)
NumPy           (pip install numpy)
scikit-learn    (pip install scikit-learn)
```

### Run
```bash
cd proctorsense/
pip install flask numpy scikit-learn
python app.py
# → http://localhost:5050
```

Open `http://localhost:5050` in Chrome/Firefox.
Grant camera + microphone permissions when prompted.

### File Structure
```
proctorsense/
├── app.py              ← Flask backend + IsolationForest
├── start.sh            ← convenience startup
├── static/
│   └── index.html      ← full frontend (MediaPipe + Web Audio + UI)
├── screenshots/        ← saved PNG frames + JSON evidence records
└── README.md
```

---

## Flagging Policy

**Candidates are NEVER directly disqualified.**

All flags are:
1. Logged with timestamp and feature snapshot
2. A canvas frame is captured and saved as PNG evidence
3. Sent to the proctor dashboard via SSE
4. Aggregated into a downloadable JSON report

The proctor reviews all flags and makes the final decision.

---

## API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve frontend |
| `/api/stream` | GET (SSE) | Real-time event stream |
| `/api/face` | POST | Face landmark data |
| `/api/voice` | POST | Voice energy + VAD |
| `/api/text` | POST | Paste/keystroke events |
| `/api/screenshot` | POST | Canvas frame upload |
| `/api/report` | GET | Full session report JSON |
| `/api/reset` | POST | Reset session |
| `/screenshots/<file>` | GET | Serve saved images |

---

## MediaPipe Notes

MediaPipe loads from `cdn.jsdelivr.net` — requires internet on the candidate's machine (normal in any online OA). The frontend gracefully falls back to motion-based tracking if MediaPipe CDN is unavailable.

For fully offline deployment, host MediaPipe WASM files locally and update the `locateFile` path.
