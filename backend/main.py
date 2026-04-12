"""
FastAPI Backend for EightFold HireMind + SENTINEL

Provides REST API and WebSocket endpoints for:
  - Interview session management
  - Real-time audio processing with Deepgram STT
  - TTS for interviewer questions
  - SENTINEL multimodal monitoring
  - Real-time event streaming to React frontend
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hiremind_backend")

# Import SENTINEL
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sentinel.orchestrator import SentinelOrchestrator
from sentinel.config import REPORT_DIR, SNAPSHOT_DIR

# Import integrations
from .integrations.deepgram_stt import DeepgramSTT
from .integrations.gemini_tts import GeminiTTS
from .integrations.gemini_llm import GeminiLLM


# ═══════════════════════════════════════════════════════════
# PYDANTIC MODELS FOR REQUEST/RESPONSE
# ═══════════════════════════════════════════════════════════
class InterviewStartRequest(BaseModel):
    """Request body for starting an interview"""
    candidate_name: str
    experience_tier: str
    jd: str
    competencies: str


class InterviewStartResponse(BaseModel):
    """Response for interview start"""
    session_id: str
    question: str
    audio_url: str
    turn: int = 0


class InterviewSubmitResponse(BaseModel):
    """Response for submitting a candidate response"""
    turn: int
    transcript: str
    next_question: Optional[str] = None
    audio_url: Optional[str] = None
    final_report: Optional[dict] = None


# ═══════════════════════════════════════════════════════════
# GLOBAL STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════
class InterviewSession:
    """Represents an active interview session."""
    
    def __init__(self, session_id: str, candidate_name: str, experience_tier: str, jd: str, competencies: str):
        self.session_id = session_id
        self.candidate_name = candidate_name
        self.experience_tier = experience_tier
        self.jd = jd
        self.competencies = competencies
        self.started_at = datetime.now()
        
        # Initialize SENTINEL
        self.sentinel = SentinelOrchestrator()
        self.sentinel.on_session_start(candidate_name, experience_tier)
        
        # Interview state
        self.current_turn = 0
        self.total_turns = 0
        self.completed = False
        self.interview_transcript = []
        
        # Active WebSocket connections for this session
        self.websocket_connections = []
    
    async def add_connection(self, websocket: WebSocket):
        """Register a WebSocket client."""
        await websocket.accept()
        self.websocket_connections.append(websocket)
    
    async def broadcast_event(self, event_type: str, data: dict):
        """Broadcast event to all connected clients."""
        message = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        for ws in self.websocket_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
    
    async def remove_connection(self, websocket: WebSocket):
        """Deregister a WebSocket client."""
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)


# Global session store
SESSIONS: dict[str, InterviewSession] = {}


# ═══════════════════════════════════════════════════════════
# LIFESPAN MANAGEMENT
# ═══════════════════════════════════════════════════════════
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage app startup and shutdown.
    Initialize services, create directories, etc.
    """
    logger.info("Starting HireMind Backend...")
    
    # Create output directories
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    
    # Initialize integrations
    logger.info("Initializing TTS, STT, and LLM services...")
    
    yield
    
    logger.info("Shutting down HireMind Backend...")
    # Cleanup: close any active SENTINEL sessions
    for session in SESSIONS.values():
        try:
            session.sentinel.on_session_end()
        except Exception as e:
            logger.error(f"Error ending session: {e}")


# ═══════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════
app = FastAPI(
    title="HireMind Backend",
    description="AI-powered technical interviewer with multimodal integrity monitoring",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(SESSIONS)
    }


# ═══════════════════════════════════════════════════════════
# INTERVIEW MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════
@app.post("/api/interview/start")
async def start_interview(request: InterviewStartRequest):
    """
    Start a new interview session.
    
    Args:
        request: Interview configuration (JSON body)
    
    Returns:
        session_id: Unique identifier for this session
        question: First question from the interviewer
        audio_url: URL to download TTS audio of the question
    """
    import uuid
    session_id = str(uuid.uuid4())
    
    try:
        # Create session
        session = InterviewSession(
            session_id=session_id,
            candidate_name=request.candidate_name,
            experience_tier=request.experience_tier,
            jd=request.jd,
            competencies=request.competencies
        )
        SESSIONS[session_id] = session
        
        # Get initial greeting + first question from LLM
        llm = GeminiLLM()
        
        greeting_question = await llm.generate_question(
            competencies=request.competencies,
            current_turn=0,
            previous_responses=None
        )
        
        # Generate TTS audio
        tts = GeminiTTS()
        audio_bytes = await tts.synthesize(greeting_question)
        
        # Save audio and get URL
        audio_filename = f"question_{session_id}_0.mp3"
        audio_path = os.path.join(REPORT_DIR, audio_filename)
        with open(audio_path, 'wb') as f:
            f.write(audio_bytes)
        
        session.interview_transcript.append({
            "turn": 0,
            "role": "interviewer",
            "text": greeting_question
        })
        
        return JSONResponse({
            "session_id": session_id,
            "candidate_name": request.candidate_name,
            "current_turn": 0,
            "question": greeting_question,
            "audio_url": f"/api/interview/{session_id}/audio/0"
        })
    
    except Exception as e:
        logger.error(f"Error starting interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/interview/{session_id}/submit-response")
async def submit_audio_response(
    session_id: str,
    audio_file: UploadFile = File(...)
):
    """
    Submit audio response from candidate.
    
    1. Transcribe audio using Deepgram STT
    2. Run SENTINEL monitoring on audio/video frames
    3. Evaluate response using LLM
    4. Generate next question or conclude interview
    5. Return next question + audio
    """
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Read audio bytes
        audio_bytes = await audio_file.read()
        
        # Transcribe with Deepgram
        deepgram = DeepgramSTT()
        transcript = await deepgram.transcribe(audio_bytes)
        
        logger.info(f"Candidate response (turn {session.current_turn}): {transcript}")
        
        candidate_response = transcript
        
        # Get current question from transcript
        current_question = session.interview_transcript[-1]["text"]
        
        # Run SENTINEL analysis on this turn
        sentinel_result = session.sentinel.on_turn(
            question=current_question,
            response=candidate_response
        )
        
        # Store in transcript
        session.current_turn += 1
        session.interview_transcript.append({
            "turn": session.current_turn,
            "role": "candidate",
            "text": candidate_response,
            "sentinel_data": sentinel_result
        })
        
        # Broadcast monitoring event
        await session.broadcast_event("turn_complete", {
            "turn": session.current_turn,
            "integrity_score": sentinel_result.get("integrity_score", 0),
            "classification": sentinel_result.get("classification", "CLEAN")
        })
        
        # Determine next action (more questions or conclude)
        llm = GeminiLLM()
        
        # For demo: 3 turns of questions
        if session.current_turn >= 3:
            # Generate final report
            # Extract responses and competencies from transcript
            responses = [t.get("text", "") for t in session.interview_transcript if t.get("role") == "candidate"]
            evaluations = [t.get("sentinel_data", {}) for t in session.interview_transcript if t.get("role") == "candidate"]
            
            interview_summary = await llm.generate_report(
                candidate_name=session.candidate_name,
                competencies=session.competencies,
                responses=responses,
                evaluations=evaluations,
                integrity_analysis={"experience_tier": session.experience_tier}
            )
            session.completed = True
            
            return JSONResponse({
                "session_id": session_id,
                "status": "completed",
                "report": interview_summary
            })
        else:
            # Generate next question
            next_question = await llm.generate_question(
                competencies=session.competencies,
                current_turn=session.current_turn,
                previous_responses=session.interview_transcript
            )
            
            # Generate TTS
            tts = GeminiTTS()
            audio_bytes = await tts.synthesize(next_question)
            
            # Save audio
            audio_filename = f"question_{session_id}_{session.current_turn}.mp3"
            audio_path = os.path.join(REPORT_DIR, audio_filename)
            with open(audio_path, 'wb') as f:
                f.write(audio_bytes)
            
            session.interview_transcript.append({
                "turn": session.current_turn,
                "role": "interviewer",
                "text": next_question
            })
            
            return JSONResponse({
                "session_id": session_id,
                "current_turn": session.current_turn,
                "question": next_question,
                "audio_url": f"/api/interview/{session_id}/audio/{session.current_turn}",
                "integrity_feedback": {
                    "score": sentinel_result.get("integrity_score", 0),
                    "classification": sentinel_result.get("classification", "CLEAN")
                }
            })
    
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/interview/{session_id}/audio/{turn}")
async def get_question_audio(session_id: str, turn: int):
    """Stream audio file for a specific turn."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    audio_filename = f"question_{session_id}_{turn}.mp3"
    audio_path = os.path.join(REPORT_DIR, audio_filename)
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio not found")
    
    return StreamingResponse(
        open(audio_path, "rb"),
        media_type="audio/mpeg"
    )


@app.websocket("/ws/interview/{session_id}")
async def websocket_monitoring(websocket: WebSocket, session_id: str):
    """
    WebSocket connection for real-time monitoring events.
    
    Broadcast events:
      - turn_complete: Turn analysis complete with scores
      - gaze_drift: Eye tracking event
      - object_detected: Object detected on screen
      - lip_sync_mismatch: Audio-visual mismatch
      - session_end: Interview concluded
    """
    session = SESSIONS.get(session_id)
    if not session:
        await websocket.close(code=1008)
        return
    
    await session.add_connection(websocket)
    
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            # Echo or process client messages if needed
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await session.remove_connection(websocket)


@app.post("/api/interview/{session_id}/end")
async def end_interview(session_id: str):
    """End the interview session and generate final report."""
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # End SENTINEL session
        pdf_path = session.sentinel.on_session_end()
        
        # Generate final report
        llm = GeminiLLM()
        
        # Extract responses and competencies from transcript
        responses = [t.get("text", "") for t in session.interview_transcript if t.get("role") == "candidate"]
        evaluations = [t.get("sentinel_data", {}) for t in session.interview_transcript if t.get("role") == "candidate"]
        
        final_report = await llm.generate_report(
            candidate_name=session.candidate_name,
            competencies=session.competencies,
            responses=responses,
            evaluations=evaluations,
            integrity_analysis={"experience_tier": session.experience_tier}
        )
        
        # Save report
        report_path = os.path.join(REPORT_DIR, f"report_{session_id}.json")
        with open(report_path, 'w') as f:
            json.dump(final_report, f, indent=2)
        
        session.completed = True
        
        return JSONResponse({
            "status": "completed",
            "session_id": session_id,
            "report": final_report,
            "pdf_path": pdf_path
        })
    
    except Exception as e:
        logger.error(f"Error ending interview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════
def _build_system_prompt(jd: str, competencies: str, candidate_name: str) -> str:
    """Build the system prompt for the LLM interviewer."""
    return f"""You are HireMind, a high-signal AI interviewer specialized in detecting conceptual mastery.

CANDIDATE: {candidate_name}
JOB DESCRIPTION: {jd}
COMPETENCIES TO ASSESS: {competencies}

You operate as a three-phase agent:
1. INTERVIEWER: Ask deep, probing questions that reveal understanding of HOW and WHY
2. DEPTH EVALUATOR: Internally classify responses as SURFACE, PARTIAL, or DEEP
3. REPORT GENERATOR: Create comprehensive evaluation after all questions

Guidelines:
- Ask one question at a time
- Probe mechanisms, trade-offs, and real-world constraints
- Do NOT ask yes/no or vocabulary questions
- Route based on depth: DEEP→next competency, PARTIAL→follow-up, SURFACE→socratic probe
- After 2 follow-ups on same competency, advance to next
- Be professional, objective, unflinching
- Do not telegraph scoring

Respond with ONLY the question to ask - no additional text.
"""


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
