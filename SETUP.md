# ProctorSense AI — Online Assessment Anomaly Detector

Real-time anomaly detection for online assessments using **MediaPipe**,  **Web Audio API (VAD)**, and **Isolation Forest** (sklearn).

---

## 🎯 Features

### **1. Eye & Neck Movement Detection (MediaPipe)**
- Real-time iris tracking with **468 facial landmarks + iris points**
- Gaze deviation detection (looking left/right/up/down)
- Head tilt/neck angle monitoring
- Blink rate analysis (normal: 12-20 blinks/min)

### **2. Voice Anomaly Detection (Web Audio API + VAD)**
- 16kHz mono audio capture from microphone
- **RMS-based Voice Activity Detection** (VAD)
- Speech segment detection with state machine
- Isolation Forest scoring for voice patterns

### **3. Text Anomaly Detection**
- **Paste event detection** — immediately flags when candidate pastes text
- **N-gram similarity matching** — compares against known LeetCode solution fingerprints
- **Typing velocity** — flags abnormal bursts (>20 chars in <300ms)
- **Tab switch detection** — logs when candidate leaves the exam window

### **4. Isolation Forest Ensemble**
- **12-dimensional feature vector** combining all sensors
- Rolling window of 200 samples
- Weighted scoring: Eye (20%) + Neck (10%) + Voice (20%) + IF (25%) + Paste (15%) + Velocity (10%)
- Contamination rate: 8%

### **5. Screenshot Evidence**
- Automatic frame capture for each anomaly
- Annotated with flag type and timestamp
- Saved as PNG + JSON metadata
- Accessible to proctors for review

### **6. Human Review (Not Auto-Rejection)**
- **Candidates are NEVER automatically disqualified**
- All flags logged with severity level
- Full report downloadable as JSON
- Proctors make final decision

---

## 📋 Setup Instructions

### **Step 1: Install Python Dependencies**

```bash
cd /home/uday/code/Anomaly
pip install -r requirements.txt
```

Or manually:
```bash
pip install Flask==3.0.0
pip install numpy==1.24.3
pip install scikit-learn==1.3.0
```

### **Step 2: Run the Backend**

```bash
python app.py
```

You should see:
```
============================================================
  ProctorSense AI Backend
  Real-time Anomaly Detection (Isolation Forest)
  http://localhost:5050
============================================================
 * Running on http://0.0.0.0:5050
```

Or use the script:
```bash
bash start.sh
```

### **Step 3: Open in Browser**

Open **http://localhost:5050** in Chrome/Firefox/Edge

### **Step 4: Grant Permissions**

When prompted, allow:
- ✅ Camera access (for MediaPipe face tracking)
- ✅ Microphone access (for VAD voice detection)

The system will start monitoring once permissions are granted.

---

## 🏗️ Project Structure

```
Anomaly/
├── app.py                  # Flask backend + IsolationForest
├── requirements.txt        # Python dependencies
├── start.sh               # Startup script
├── static/
│   └── index.html         # Full frontend (HTML + CSS + JS)
├── screenshots/           # Saved evidence frames (PNG + JSON)
├── README.md              # This file
└── README (1).md          # Original documentation
```

---

## 🚀 How It Works

### **Frontend → Backend → Decisions**

1. **Frontend** (index.html)
   - MediaPipe detects face + landmarks
   - Web Audio API captures voice at 16kHz
   - Tracks paste events and typing patterns
   - Sends real-time data to backend via POST

2. **Backend** (app.py)
   - Receives data on `/api/face`, `/api/voice`, `/api/text`
   - Runs Isolation Forest on 12-dimensional feature vector
   - Computes anomaly scores per channel
   - Emits real-time updates via SSE `/api/stream`

3. **Report Generation**
   - All flags timestamped with snapshot
   - Screenshots sent to `/screenshots/` folder
   - JSON report downloadable from proctor dashboard
   - **Higher authorities review before disqualification**

---

## 📊 Anomaly Scoring

### **Overall Risk Score (0-100)**

```
Overall = 0.20×Eye + 0.10×Neck + 0.20×Voice + 0.25×IsolationForest + 0.15×Paste + 0.10×Velocity
```

**Status Badges:**
- 🟢 **0-30**: Monitoring Active
- 🟡 **30-60**: Suspicious Activity
- 🔴 **60+**: Anomalies Detected → Flagged for Review

---

## 🔍 Detection Details

| Channel | Detection Method | Threshold |
|---------|------------------|-----------|
| **Eye Gaze** | Iris position relative to eye corners | Deviation > 0.35 |
| **Neck Tilt** | Cheek landmark angle | Angle > 20° |
| **Blink Rate** | Eye Aspect Ratio (EAR) | <8 or >30 blinks/min |
| **Voice** | RMS energy + state machine | Energy > 0.015, 3+ frames |
| **Paste** | `onpaste` event | Any paste event |
| **Typing** | Character delta / time delta | >20 chars in <300ms |
| **Tab Switch** | `visibilitychange` API | Any switch = flag |

---

## 🔐 Data Privacy & Ethics

✅ **No external data transmission** — all processing on local machine  
✅ **No identity tracking** — only behavioral anomalies  
✅ **Human review mandatory** — automatic flagging only, no auto-disqualification  
✅ **Evidence preservation** — all flags have screenshots for audit trail  
✅ **Transparency** — candidates see all raw data in report  

---

## 🛠️ API Reference

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

## 📱 Browser Compatibility

- ✅ **Chrome/Chromium** (recommended)
- ✅ **Firefox**
- ✅ **Safari** (no Blink support)
- ✅ **Edge**

**Requirements:**
- Webcam + Microphone
- Internet (for MediaPipe CDN)
- JavaScript enabled

---

## 🧪 Testing

### **Simulate Paste Event**
1. Open Q4 (coding question)
2. Try pasting code → Instant flag + screenshot

### **Simulate Gaze Deviation**
1. Look left/right during exam
2. Watch gaze meter spike on dashboard

### **Simulate Voice Detection**
1. Speak during exam
2. Watch waveform animate + speech event logged

### **Simulate Typing Burst**
1. Try typing 30+ chars in <300ms
2. Flag raised for abnormal velocity

---

## 📝 Sample Question Types

- **MCQs**: Data Structures, OS, Networks
- **Coding Easy**: Two Sum (LeetCode-style)
- **Coding Medium**: LRU Cache
- **System Design**: Rate Limiter  
- **Conceptual**: ACID vs BASE

Total: **7 Questions × 45 minutes** (hardcoded in demo)

---

## 🚨 Common Issues & Fixes

### **Issue: "Backend: Offline"**
```bash
# Make sure Flask is running
python app.py  # or bash start.sh
# Check port 5050 is available
lsof -i :5050
```

### **Issue: Camera not detected**
```bash
# Grant permissions in browser settings
# For Linux: check /dev/video0
ls -la /dev/video*
```

### **Issue: MediaPipe CDN fails**
- Frontend automatically falls back to motion-based tracking
- Less accurate but still functional
- Add `?offline` query to use local WASM files (advanced)

### **Issue: No sound detected**
- Check microphone permissions
- Test microphone: `pactl list sources`
- Check browser privacy settings

---

## 📚 Technologies Used

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | HTML5 + Vanilla JS | No dependencies |
| Face Tracking | MediaPipe Facemesh | 468 landmarks + iris |
| Voice Detection | Web Audio API | 16kHz FFT + RMS |
| Anomaly ML | scikit-learn | IsolationForest |
| Backend | Flask + SSE | Real-time streaming |
| Visualization | Canvas 2D | Overlay graphics |

---

## 📄 References

- [MediaPipe FaceMesh Docs](https://mediapipe.dev/solutions/face_mesh)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [scikit-learn IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [Flask SSE](https://flask.palletsprojects.com/en/3.0.x/)

---

## 📞 Support

For issues or questions:
1. Check the event log in the right panel
2. Download the JSON report for debugging
3. Check browser console (F12 → Console tab)
4. Verify backend is running: `curl http://localhost:5050/`

---

**Built with ❤️ for APOGEE 2026 · Track C**

*Last Updated: 2026-04-12*
