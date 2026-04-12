# HireMind Architecture Document

## System Design Overview

HireMind is a full-stack technical interview platform combining:
- **Frontend**: React.js web application for interview UI
- **Backend**: FastAPI server orchestrating SENTINEL monitoring + voice I/O
- **Voice Pipeline**: Deepgram (STT) + Google Cloud (TTS) + Groq (LLM)
- **Monitoring**: SENTINEL multimodal integrity analysis

### High-Level Architecture

```
                           ┌─────────────────────────┐
                           │   React.js Frontend     │
                           │   (Port 5173)           │
                           │                         │
                           │ ┌─────────────────────┐ │
                           │ │ ConfigPanel         │ │
                           │ │ - Role selection    │ │
                           │ │ - JD/Competencies   │ │
                           │ └─────────────────────┘ │
                           │                         │
                           │ ┌─────────────────────┐ │
                           │ │ InterviewSession    │ │
                           │ │ - Q&A flow          │ │
                           │ │ - Audio recording   │ │
                           │ │ - TTS playback      │ │
                           │ └─────────────────────┘ │
                           │                         │
                           │ ┌─────────────────────┐ │
                           │ │ MonitoringDash      │ │
                           │ │ - Score gauge       │ │
                           │ │ - Real-time events  │ │
                           │ └─────────────────────┘ │
                           │                         │
                           │ ┌─────────────────────┐ │
                           │ │ AudioRecorder       │ │
                           │ │ - MediaRecorder API │ │
                           │ │ - WebM recording    │ │
                           │ └─────────────────────┘ │
                           │                         │
                           │ ┌─────────────────────┐ │
                           │ │ VideoMonitor        │ │
                           │ │ - getUserMedia()    │ │
                           │ │ - Canvas overlays   │ │
                           │ └─────────────────────┘ │
                           └────────┬────────────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │ HTTP + WebSocket               │
                    ▼                                ▼
            ┌──────────────────────┐        ┌────────────────────┐
            │ REST Endpoints       │        │ WebSocket Stream   │
            │ /api/interview/*     │        │ /ws/interview/*    │
            └──────────────────────┘        └────────────────────┘
                    │                                │
                    ▼                                ▼
            ┌────────────────────────────────────────────────┐
            │         FastAPI Backend (Port 8000)            │
            │                                                │
            │  ┌──────────────────────────────────────────┐ │
            │  │ Session Management                        │ │
            │  │ - Session store (dict/Redis)              │ │
            │  │ - WebSocket handlers                      │ │
            │  │ - CORS middleware                         │ │
            │  └──────────────────────────────────────────┘ │
            │                                                │
            │  ┌──────────────────────────────────────────┐ │
            │  │ Interview Endpoints                       │ │
            │  │ POST /api/interview/start                │ │
            │  │ POST /api/interview/{id}/submit-response │ │
            │  │ GET /api/interview/{id}/audio/{turn}     │ │
            │  │ POST /api/interview/{id}/end             │ │
            │  │ WS /ws/interview/{id}                    │ │
            │  └──────────────────────────────────────────┘ │
            │                                                │
            │  ┌──────────────────────────────────────────┐ │
            │  │ SENTINEL Orchestrator                     │ │
            │  │ - Session-scoped instance                │ │
            │  │ - Multimodal analysis coordination        │ │
            │  │ - Event broadcasting                      │ │
            │  │ - Report generation                       │ │
            │  └──────────────────────────────────────────┘ │
            │                                                │
            │  ┌──────────────────────────────────────────┐ │
            │  │ Integration Modules                       │ │
            │  │                                          │ │
            │  │ ┌─────────────┐ ┌─────────────┐        │ │
            │  │ │ Deepgram    │ │ Google TTS  │        │ │
            │  │ │ STT Module  │ │ TTS Module  │        │ │
            │  │ └─────────────┘ └─────────────┘        │ │
            │  │                                          │ │
            │  │ ┌──────────────────────────────────┐    │ │
            │  │ │ Groq LLM Module                  │    │ │
            │  │ │ - Question generation            │    │ │
            │  │ │ - Response evaluation            │    │ │
            │  │ │ - Report generation              │    │ │
            │  │ └──────────────────────────────────┘    │ │
            │  └──────────────────────────────────────────┘ │
            │                                                │
            └────────┬───────────────────────┬────────────────┘
                     │                       │
        ┌────────────┴─────────┐    ┌────────┴──────────┐
        │ SENTINEL Backend     │    │ External APIs    │
        │ ┌─────────────────┐  │    │ ┌──────────────┐ │
        │ │ Agents:         │  │    │ │ Deepgram     │ │
        │ │ - ECA (Audio)   │  │    │ │ - nova-2 STT │ │
        │ │ - LCA (Lexical) │  │    │ └──────────────┘ │
        │ │ - SDA (Semantic)│  │    │                  │
        │ │ - AIGA (AI Det) │  │    │ ┌──────────────┐ │
        │ │ - VSA (Voice)   │  │    │ │ Google Cloud │ │
        │ │ - MIA (Modal)   │  │    │ │ - TTS Neural │ │
        │ └─────────────────┘  │    │ └──────────────┘ │
        │                       │    │                  │
        │ ┌─────────────────┐  │    │ ┌──────────────┐ │
        │ │ Models:         │  │    │ │ Groq         │ │
        │ │ - MediaPipe     │  │    │ │ - LLaMA 3.3  │ │
        │ │ - spaCy         │  │    │ │ - Inference  │ │
        │ │ - Sentence Transformer  │ │ - Embeddings │ │
        │ │ - MFCC          │  │    │ └──────────────┘ │
        │ │ - YOLOv8        │  │    │                  │
        │ └─────────────────┘  │    └──────────────────┘
        │                       │
        │ ┌─────────────────┐  │
        │ │ Storage:        │  │
        │ │ - Session Store │  │
        │ │ - Reports/      │  │
        │ │ - Snapshots/    │  │
        │ └─────────────────┘  │
        └───────────────────────┘
```

---

## Component Details

### Frontend Components

#### 1. ConfigPanel.jsx
- **Purpose**: Initial interview setup
- **Inputs**: Candidate name, experience tier, role preset
- **Outputs**: Session ID, initial question, TTS audio URL
- **Key Functions**:
  - `handlePresetSelect()`: Load role-specific JD and competencies
  - `handleStartInterview()`: POST to `/api/interview/start`
- **State**: candidateName, selectedPreset, jd, competencies, isLoading

#### 2. InterviewSession.jsx
- **Purpose**: Main interview orchestration
- **Lifecycle**:
  1. Loads initial question and TTS audio
  2. Plays audio automatically
  3. Waits for candidate to record response
  4. Submits audio blob to `/submit-response`
  5. Receives next question or final report
  6. Updates monitoring dashboard
  7. Repeats or displays report
- **WebSocket Integration**: Real-time score updates
- **Key Functions**:
  - `loadQuestion()`: GET question from `/api/interview/{id}/audio/{turn}`
  - `playAudio()`: Stream TTS audio
  - `submitResponse()`: POST audio blob
  - `handleWebSocketEvent()`: Update scores/alerts
- **State**: currentTurn, question, audioUrl, isPlayingAudio, isSubmitting, integrityScore, report

#### 3. AudioRecorder.jsx
- **Purpose**: Capture candidate audio responses
- **API Used**: MediaRecorder (browser native API)
- **Recording Format**: WebM (VP8 video + Opus audio)
- **Audio Constraints**:
  ```javascript
  {
    echoCancellation: true,
    noiseSuppression: true,
    sampleRate: 16000
  }
  ```
- **Key Functions**:
  - `startRecording()`: Request microphone, initialize MediaRecorder
  - `stopRecording()`: Capture WebM blob
  - `playback()`: Test audio quality before submission
  - `onSubmit()`: Pass blob to parent
- **State**: isRecording, recordedAudio, isProcessing

#### 4. VideoMonitor.jsx
- **Purpose**: Display camera feed and monitoring info
- **API Used**: getUserMedia() for camera access
- **Features**:
  - Live video stream (mirrored for selfie view)
  - Real-time monitoring indicators
  - Placeholder for MediaPipe overlays (landmarks, gaze direction)
- **Key Functions**:
  - `initializeCamera()`: Request camera, set src=stream
  - `displayOverlays()`: Canvas rendering of landmarks (when backend sends frames)
- **State**: cameraActive, stream, error

#### 5. MonitoringDashboard.jsx
- **Purpose**: Real-time integrity visualization
- **Charts Used**: Recharts library
- **Visualizations**:
  - Score Gauge: Horizontal bar (0-100) with color gradient
  - Classification Badge: CLEAN/WATCH/FLAG/ESCALATE
  - Score Timeline: Line chart of historical scores
  - Indicator List: Active status of all monitoring features
- **Data Source**: WebSocket events from backend
- **Key Functions**:
  - `updateScore()`: WebSocket message handler
  - `formatGauge()`: Convert score to color (green→yellow→red)
  - `handleEventAlert()`: Show toast for critical events
- **State**: integrityScore, classification, scoreHistory, indicators

### Backend Endpoints

#### POST /api/interview/start
```python
Request:
{
  "candidate_name": str,
  "experience_tier": str,  # Fresher, Mid-level, Senior, Principal/Staff
  "jd": str,              # Job description
  "competencies": str     # Comma-separated list
}

Response:
{
  "session_id": str,
  "question": str,
  "audio_url": str,       # GET endpoint for TTS audio
  "turn": 0
}

Backend Flow:
1. Create new SessionManager instance with SENTINEL orchestrator
2. Call SENTINEL.on_session_start(metadata)
3. Generate initial greeting question via Groq LLM
4. Synthesize question audio via Google TTS
5. Store session in session_store[session_id]
6. Return response
```

#### POST /api/interview/{session_id}/submit-response
```python
Request:
- multipart/form-data
- audio_file: WebM blob (recorded candidate response)

Response:
{
  "turn": int,
  "transcript": str,
  "evaluation": {
    "depth": str,         # SURFACE, PARTIAL, DEEP
    "score": float,       # 1.0 to 5.0
    "routing": str        # advance, follow_up, probe
  },
  "integrity": {
    "score": float,       # 0.0 to 100.0
    "classification": str # CLEAN, WATCH, FLAG, ESCALATE
    "signals": {...}
  },
  "next_question": str or null,
  "audio_url": str or null,
  "final_report": {...} or null
}

Backend Flow:
1. Save audio file to snapshots/
2. Call Deepgram STT: audio → transcript
3. Broadcast WebSocket event: "transcription_complete"
4. Call SENTINEL.on_turn(turn_num, transcript, audio_path)
   - Runs all agents in parallel (ECA, LCA, SDA, AIGA, VSA, MIA)
   - Calculates composite integrity score
   - Returns signals with confidence scores
5. Broadcast WebSocket events: gaze_drift, object_detected, etc.
6. Call Groq LLM: evaluate(transcript, competencies) → depth, score, routing
7. Broadcast WebSocket event: "turn_complete"
8. If turn < MAX_TURNS:
   - Generate next question via Groq LLM
   - Synthesize TTS audio
   - Return next question
9. Else:
   - Generate final report via Groq LLM
   - Return report
```

#### GET /api/interview/{session_id}/audio/{turn}
```python
Response:
- content-type: audio/mpeg
- Body: MP3 audio stream (TTS-synthesized question)
- Headers: Cache-Control: public, max-age=3600

Browser:
- Plays audio in <Audio> element
- No local storage needed (streamed)
```

#### POST /api/interview/{session_id}/end
```python
Request: {} (empty)

Response:
{
  "session_id": str,
  "status": "ended",
  "report_pdf_url": str
}

Backend Flow:
1. Call SENTINEL.on_session_end()
2. Generate comprehensive report:
   - Competency scores (mean of evaluation across turns)
   - Overall impression (based on integrity analysis)
   - Hire decision (STRONG_YES, YES, MAYBE, NO, STRONG_NO)
   - Voice signature validation
   - Multimodal alignment score
3. Generate PDF report
4. Store report in reports/ directory
5. Return URL for download
```

#### WS /ws/interview/{session_id}
```python
WebSocket Events (Server → Client):

Event 1: Turn Completed
{
  "type": "turn_complete",
  "turn": int,
  "integrity_score": float,
  "classification": str,
  "evaluation": {...},
  "timestamp": str
}

Event 2: Gaze Drift Detected
{
  "type": "gaze_drift",
  "duration_ms": int,
  "severity": str,  # low, moderate, high
  "timestamp": str
}

Event 3: Object Detected
{
  "type": "object_detected",
  "class": str,     # person, phone, laptop, etc.
  "confidence": float,
  "timestamp": str
}

Event 4: Lip Sync Mismatch
{
  "type": "lip_sync_mismatch",
  "severity": str,
  "timestamp": str
}

Event 5: Voice Signature Alert
{
  "type": "voice_signature_alert",
  "consistency_score": float,
  "timestamp": str
}

Event 6: Transcription Ready
{
  "type": "transcription_complete",
  "transcript": str,
  "confidence": float,
  "timestamp": str
}
```

### SENTINEL Integration

#### SessionManager Class
```python
class SessionManager:
    def __init__(self, session_id, metadata):
        self.session_id = session_id
        self.orchestrator = SENTINEL()  # Initialize agents
        self.audio_buffers = {}
        self.video_frames = []
        self.transcripts = []
        self.scores = []
        self.events = []  # WebSocket events to broadcast
    
    async def on_turn_start(self, turn_num):
        """Initialize video/audio capture for this turn"""
        self.orchestrator.on_turn_start(turn_num)
    
    async def on_turn_end(self, audio_path, transcript):
        """Process multimodal data for completed turn"""
        # All agents run in parallel
        signals = await self.orchestrator.on_turn(
            turn_num=self.current_turn,
            transcript=transcript,
            audio_path=audio_path,
            video_frames=self.video_frames
        )
        # signals contain: gaze_drift, lip_sync, object_detection, voice_sig, etc.
        
        # Broadcast events to frontend
        for event in signals.get('events', []):
            await self.broadcast_event(event)
        
        # Return composite score
        return signals.get('integrity_score', 0.0)
    
    async def broadcast_event(self, event):
        """Send event to all connected WebSocket clients"""
        self.events.append(event)
        for ws in self.active_websockets:
            await ws.send_json(event)
```

#### Integration Points
1. **on_session_start()**: Initialize orchestrator, set metadata
2. **on_turn()**: Run all agents, return signals and video overlays
3. **on_session_end()**: Generate comprehensive report
4. **get_video_overlay()**: Get MediaPipe landmarks for frontend rendering

---

## Data Flow: Complete Interview Cycle

### Stage 1: Setup
```
1. User selects role: "Backend Engineer"
2. Frontend loads preset: JD + competencies
3. User enters name: "Alice Smith"
4. User clicks "Start Interview"

Frontend:
  POST /api/interview/start
  ├─ candidate_name: "Alice Smith"
  ├─ experience_tier: "Mid-level"
  ├─ jd: "..."
  └─ competencies: "System Design, API Architecture"

Backend:
  ├─ Create session_id: "sess_abc123def456"
  ├─ Initialize SENTINEL orchestrator
  ├─ Generate greeting question via Groq:
  │  "Tell me about your experience with system design"
  ├─ Synthesize TTS audio via Google Cloud
  └─ Return {session_id, question, audio_url}

Frontend:
  ├─ Store session_id in state
  ├─ Mount InterviewSession component
  ├─ Load audio from audio_url
  ├─ Play audio automatically
  └─ Enable recording button
```

### Stage 2: Q&A Turn
```
1. Audio finishes playing
2. User clicks "Start Recording"
3. Browser requests microphone (user grants)
4. Recording indicator shows (15 sec)
5. User speaks response (15-30 sec)
6. User clicks "Stop Recording"
7. User clicks "Submit Response"

Frontend:
  ├─ Capture audio blob (WebM format)
  ├─ POST /api/interview/{session_id}/submit-response (form-data)
  └─ Show "Processing..." spinner

Backend:
  ├─ Receive audio blob
  ├─ Save to snapshots/{session_id}_{turn}.webm
  ├─ Call Deepgram STT API
  │  ├─ Transcribe audio → "I started with a monolithic design..."
  │  └─ Add punctuation + confidence
  ├─ Broadcast WebSocket: {type: "transcription_complete", transcript: "..."}
  ├─ Call SENTINEL.on_turn(turn_num, transcript, audio_path)
  │  ├─ Run ECA (audio quality analysis)
  │  ├─ Run LCA (lexical consistency)
  │  ├─ Run SDA (semantic drift)
  │  ├─ Run AIGA (AI generation detection)
  │  ├─ Run VSA (voice signature)
  │  ├─ Run MIA (multimodal integrity)
  │  └─ Return signals + composite score
  ├─ Broadcast WebSocket events for each signal
  ├─ Call Groq LLM: evaluate(transcript, competencies)
  │  ├─ Classify depth: DEEP (score 4.5)
  │  ├─ Route: advance (move to next competency)
  │  └─ Generate feedback: "Great architectural thinking..."
  ├─ Generate next question via Groq:
  │  "Walk me through your approach to database optimization"
  ├─ Synthesize TTS audio for next question
  └─ Return {turn, transcript, evaluation, integrity, next_question, audio_url}

Frontend:
  ├─ Receive response
  ├─ Stop spinner
  ├─ Update MonitoringDashboard:
  │  ├─ integrity_score: 87.3%
  │  ├─ classification: CLEAN
  │  └─ score timeline: add data point
  ├─ Display next question: "Walk me through your approach..."
  ├─ Play next question audio
  ├─ AudioRecorder reset (ready for next response)
  └─ Repeat: Request microphone → Record → Submit
```

### Stage 3: Completion
```
After 3 turns:

Backend:
  ├─ Turn 3 response submitted
  ├─ SENTINEL analysis complete
  ├─ Call Groq LLM: generate_report()
  │  ├─ Input: All transcripts, evaluations, signals
  │  ├─ Calculate competency scores:
  │  │  ├─ System Design: (4.0 + 4.5 + 4.2) / 3 = 4.23
  │  │  └─ API Architecture: (3.8 + 4.1 + 4.0) / 3 = 4.0
  │  ├─ Determine hire signal: STRONG_YES
  │  ├─ Generate feedback narrative
  │  └─ Generate integrity analysis
  ├─ Generate PDF report via fpdf2
  ├─ Store in reports/{session_id}.pdf
  └─ Return final_report JSON

Frontend:
  ├─ Receive final_report
  ├─ Hide next question prompt
  ├─ Display report summary:
  │  ├─ Overall Signal: STRONG_YES ✓
  │  ├─ Competency Scores
  │  ├─ Feedback
  │  └─ Integrity Analysis
  ├─ Show "Download Report" button
  ├─ User clicks → PDF downloaded to device
  └─ Interview complete
```

---

## Security Considerations

### API Key Management
- All API keys stored in environment variables
- Service account JSON for Google Cloud loaded at startup
- No API keys logged or exposed in responses
- Deepgram + Groq keys rotated via environment

### Audio Data Handling
- Audio files stored temporarily in `snapshots/`
- Deleted after processing (no long-term storage)
- Optional: Encrypt audio in transit via HTTPS
- Optional: Enable Redis for temporary session caching

### CORS Policy
```python
CORSMiddleware(
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# In production: change to specific frontend domain
```

### Session Management
- Session IDs generated via `uuid4()` (cryptographically secure)
- WebSocket authentication via session ID validation
- Optional: Add JWT tokens for production

---

## Performance Characteristics

### Latency Breakdown (per turn)
| Component | Latency | Notes |
|-----------|---------|-------|
| STT (Deepgram) | 2-3s | Depends on audio length (avg 20s) |
| SENTINEL Analysis | 1-2s | Parallel agents |
| LLM Evaluation (Groq) | 3-5s | Token generation |
| TTS Synthesis (Google) | 1-2s | Depends on text length |
| **Total per turn** | **7-12s** | Negligible network latency |

### Scalability
- Single backend instance: ~100 concurrent sessions
- WebSocket events: < 100ms latency per broadcast
- Database: Redis/MongoDB scales to 1000+ sessions
- GPU: SENTINEL agents require GPU for real-time video (optional)

### Storage
- Per session: ~5 MB (10 audio files × 500KB)
- Per report: ~50 KB (PDF)
- Cleanup: Delete snapshots after session ends

---

## Future Enhancements

### Phase 2: Video Overlay Rendering
- Stream MediaPipe landmarks from backend to frontend
- Render face mesh, eye gaze direction, lip movement amplitude
- Real-time visualization of detected events

### Phase 3: Advanced Monitoring
- Implement full video frame processing pipeline
- YOLO object detection with bounding boxes
- Activity detection (phone use, looking away, etc.)

### Phase 4: Multi-Interviewer Support
- Allow panel interviews (multiple evaluators)
- Synchronized scoring and notes
- Consensus report generation

### Phase 5: Analytics Dashboard
- Interview performance analytics
- Competency benchmarking
- Hiring pattern analysis
- Candidate feedback loop

---

## Deployment Checklist

- [ ] All API keys obtained and verified
- [ ] `.env` file configured with API keys
- [ ] Google Cloud service account JSON downloaded
- [ ] Backend dependencies installed (`pip install -r requirements.txt`)
- [ ] spaCy model downloaded (`python -m spacy download en_core_web_sm`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Backend running and healthy (`http://localhost:8000/docs`)
- [ ] Frontend running and accessible (`http://localhost:5173`)
- [ ] Complete test interview to verify all components
- [ ] Review backend logs for errors
- [ ] Review browser console for warnings
- [ ] Database/Redis configured (optional for production)
- [ ] HTTPS certificates obtained (for production)
- [ ] Docker image built and tested
- [ ] Monitoring dashboard (Grafana/Datadog) configured (optional)
- [ ] Error tracking (Sentry) configured (optional)

---

## Troubleshooting Guide

**Issue**: Backend fails to start
- **Check**: `GROQ_API` is valid and has quota
- **Fix**: Verify API key in `.env`

**Issue**: TTS audio not playing
- **Check**: `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON
- **Check**: Service account permissions for TTS API
- **Fix**: Update Google Cloud credentials

**Issue**: STT transcription empty
- **Check**: Deepgram API key valid
- **Check**: Audio file is valid WebM format
- **Fix**: Test audio file with Deepgram API directly

**Issue**: WebSocket connection fails
- **Check**: Backend running on port 8000
- **Fix**: Check firewall rules

**Issue**: SENTINEL agents not initialized
- **Check**: spaCy model installed
- **Fix**: Run `python -m spacy download en_core_web_sm`

