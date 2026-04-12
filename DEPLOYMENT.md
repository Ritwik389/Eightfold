# HireMind: React + FastAPI AI Interview Platform

A modern, full-stack technical interview platform with real-time voice interaction, multimodal integrity monitoring, and AI-powered assessment.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│              React.js Frontend (Port 5173)                  │
│        ├─ Config Panel (setup interview parameters)         │
│        ├─ Interview Session (main interview UI)             │
│        ├─ Video Monitor (WebRTC camera + overlays)          │
│        ├─ Audio Recorder (WebM audio recording)             │
│        └─ Monitoring Dashboard (real-time integrity scores) │
└────────────┬────────────────────────────────────────────────┘
             │ HTTP + WebSocket
             ▼
┌─────────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                      │
│        ├─ /api/interview/start (session init)               │
│        ├─ /api/interview/{id}/submit-response (STT + eval)  │
│        ├─ /api/interview/{id}/audio/{turn} (TTS stream)    │
│        ├─ /ws/interview/{id} (real-time monitoring)         │
│        └─ /api/interview/{id}/end (report generation)       │
└────────────┬────────────────────────────────────────────────┘
             │ SDK Integration
    ┌────────┴───────────┬──────────────┐
    ▼                    ▼              ▼
  SENTINEL     Deepgram STT      Gemini API
  Multimodal   (Audio→Text)      (LLM + TTS)
  Monitoring   ("nova-2" model)  (aistudio.google.com)
```

## Setup Instructions

### Prerequisites

- **Node.js** 18+ (for frontend)
- **Python** 3.11+ (for backend)
- **Docker** & **Docker Compose** (optional, for containerized deployment)
- API Keys:
  - `GEMINI_API_KEY`: Gemini API key from https://aistudio.google.com/app/apikey (for LLM + TTS)
  - `DEEPGRAM_API_KEY`: Deepgram API key for STT

### 1. Environment Setup

Create `.env` file in project root:

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
DEEPGRAM_API_KEY=your_deepgram_api_key

# Model configuration (optional)
GEMINI_LLM_MODEL=gemini-2.0-flash
GEMINI_TTS_VOICE=Kore

# Backend
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Get your API keys from:
- **Gemini**: https://aistudio.google.com/app/apikey (for LLM + TTS)
- **Deepgram**: https://console.deepgram.com (for STT)

### 2. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run development server
uvicorn main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger UI

### 3. Frontend Setup (React + Vite)

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will be available at `http://localhost:5173`

### 4. Docker Deployment (Optional)

```bash
# From project root
docker-compose up -d

# Check services
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## Key Features

### 1. Voice-Enabled Interview

**Speech-to-Text (STT):**
- Candidate responses transcribed using Deepgram SDK
- "nova-2" model for highest accuracy
- Real-time transcription with punctuation
- Language detection and multilingual support
- Diarization support for background speaker detection

**Text-to-Speech (TTS):**
- Questions synthesized using Gemini API
- Natural, professional voice delivery
- Multiple voice options available (Puck, Charon, Kore, Fenrir, Aoide)
- Audio streamed directly to browser

### 2. Real-Time Multimodal Monitoring

**Backend (SENTINEL):**
- Eye tracking with MediaPipe (iris landmarks)
- Lip aperture analysis for lip-sync correlation
- Gaze drift detection (sustained off-screen staring)
- YOLOv8 object detection (phones, secondary persons, monitor duplication)
- Voice signature verification (d-vector embeddings)
- VSA (Voice Signature Agent) for speaker consistency
- MIA (Multimodal Integrity Agent) for audio-visual correlation
- Real-time integrity score calculation

**Frontend (React):**
- Real-time integrity score gauge (0-100%)
- Classification badges (CLEAN, WATCH, FLAG, ESCALATE)
- Score timeline visualization with Recharts
- Active monitoring indicators
- WebSocket-based event streaming
- Live video feed with tracking overlays (prepared for backend annotation)

### 3. Interview Flow

```
User Setup
  ↓
Select role preset or configure custom JD/competencies
  ↓
Start Interview
  ↓
Initialize SENTINEL + create HTTP session
  ↓
Load Initial Question + Generate TTS Audio
  ↓
Display Question + Play Audio
  ↓
Candidate Records Response (WebM audio)
  ↓
Submit Response
  ├─ Backend: Deepgram STT transcription
  ├─ Backend: SENTINEL multimodal analysis
  ├─ Backend: Gemini LLM depth evaluation
  └─ Backend: Real-time WebSocket updates
  ↓
Next Question Generated + TTS Audio
  ↓
Repeat 2-3 turns
  ↓
Generate Final Report
  ├─ Competency scores
  ├─ Hire signal
  ├─ Feedback
  └─ Integrity annex with SENTINEL signals
  ↓
Display Report + Download PDF
```

### 4. Integrity Assessment Signals

The backend analyzes:
- **Lexical Consistency (LCA)**: Flesch-Kincaid grade level across turns
- **Semantic Drift (SDA)**: Embedding-based coherence using paraphrase-MiniLM-L6-v2
- **AI Generation Detection (AIGA)**: Burstiness, hedge language, temporal anchors, structural perfection
- **Voice Signature (VSA)**: Speaker verification with d-vector embeddings and MFCC fallback
- **Multimodal Integrity (MIA)**:
  - Gaze drift events (eyes off-screen >2 sec)
  - Lip-sync mismatches (audio VAD vs lip aperture)
  - Object detection (secondary persons, phones, etc.)
  - Composite VSA+lip-sync events (highest confidence)

---

## API Endpoints

### Interview Management

**POST** `/api/interview/start`
```json
{
  "candidate_name": "Alice Smith",
  "experience_tier": "Mid-level",
  "jd": "Backend engineer...",
  "competencies": "System Design, API Design, ..."
}
```
Returns: `{ session_id, question, audio_url }`

**POST** `/api/interview/{session_id}/submit-response`
- Form data: `audio_file` (WebM blob)
- Returns: Next question OR final report

**GET** `/api/interview/{session_id}/audio/{turn}`
- Returns: MP3 audio stream for TTS of question

**POST** `/api/interview/{session_id}/end`
- Returns: Final report with integrity analysis

**WS** `/ws/interview/{session_id}`
- Real-time event stream: turn_complete, gaze_drift, object_detected, etc.

---

## Performance Optimizations

1. **STT Optimization:**
   - Async processing with Deepgram SDK
   - WebM audio compression (reduces bandwidth 60-70%)
   - Streaming transcription for real-time feedback

2. **TTS Optimization:**
   - MP3 caching (same question re-requests served from cache)
   - Neural voice synthesis with optimized speaking rate
   - Pregenerated audio for next turn while candidate speaks

3. **Frontend Optimization:**
   - React component memoization
   - Recharts chart lazy-loading
   - WebRTC adaptive bitrate
   - Service worker for offline resilience

4. **Backend Optimization:**
   - ThreadPoolExecutor for parallel agent execution
   - Redis caching layer (optional)
   - Async/await throughout (uvicorn + asyncio)
   - Preloaded ML models (MediaPipe, spaCy, sentence-transformers)

---

## Troubleshooting

### Deepgram STT Not Working
- Check `DEEPGRAM_API_KEY` is set and valid
- Verify audio format is WebM (browser MediaRecorder default)
- Check network connectivity to Deepgram API
- Review Deepgram quota usage

### Gemini LLM/TTS Not Working
- Check `GEMINI_API_KEY` is set and valid
- Verify key from https://aistudio.google.com/app/apikey
- Check network connectivity to Gemini API
- Review Gemini API quota/rate limits
- Backend logs will show errors: `docker-compose logs backend | grep Gemini`

### Camera/Microphone Access Denied
- Browser must be served over HTTPS (except localhost)
- User must grant permissions when prompted
- Check browser settings: Settings → Privacy & Security → Site Permissions

### WebSocket Connection Failed
- Ensure backend is running on port 8000
- Check firewall rules
- Verify session ID is valid

### Interview Report Not Generating
- Check Gemini API key is valid and has sufficient quota
- Verify LLM inference isn't timing out (30s timeout enforced)
- Check backend logs for model loading errors

---

## File Structure

```
EightFold/
├── backend/
│   ├── main.py                          # FastAPI app + endpoints
│   ├── requirements.txt
│   └── integrations/
│       ├── deepgram_stt.py              # Deepgram STT SDK
│       ├── gemini_tts.py                # Gemini TTS SDK
│       └── gemini_llm.py                # Gemini LLM inference
├── frontend/
│   ├── src/
│   │   ├── App.jsx                      # Root component
│   │   ├── index.css                    # Global styles
│   │   └── components/
│   │       ├── ConfigPanel.jsx          # Setup UI
│   │       ├── InterviewSession.jsx     # Main interview
│   │       ├── VideoMonitor.jsx         # Camera + overlays
│   │       ├── AudioRecorder.jsx        # Audio recording
│   │       ├── MonitoringDashboard.jsx  # Integrity scores
│   │       └── *.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── sentinel/                             # SENTINEL agents (preserved)
├── docker-compose.yml
├── Dockerfile.backend
└── .env
```

---

## Development Workflow

1. **Backend Development:**
   ```bash
   cd backend
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

2. **Frontend Development:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Testing:**
   ```bash
   # Backend: Navigate to http://localhost:8000/docs
   # Frontend: Navigate to http://localhost:5173
   ```

4. **Building for Production:**
   ```bash
   # Backend: Python app is production-ready
   # Frontend: npm run build (outputs to dist/)
   # Deployment: Use docker-compose for containerized deployment
   ```

---

## Next Steps

1. Set up API keys (Gemini and Deepgram from their respective consoles)
2. Install dependencies for backend and frontend
3. Run `docker-compose up` or start services manually
4. Open `http://localhost:5173` in browser
5. Configure interview and start a session

---

## License

Proprietary - EightFold AI Technical Interview Platform

## Support

For issues or questions:
1. Check backend logs: `docker-compose logs backend`
2. Check frontend console: Browser DevTools → Console
3. Review API documentation: `http://localhost:8000/docs`
4. See [GEMINI_MIGRATION.md](GEMINI_MIGRATION.md) for Gemini setup details
