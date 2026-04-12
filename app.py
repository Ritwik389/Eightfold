<<<<<<< Updated upstream
"""
ProctorSense AI — Real-Time OA Anomaly Detection Backend
Flask + SSE + Isolation Forest (sklearn)
No external socket libraries needed.
=======
import streamlit as st
from groq import Groq
import re
import os
from fpdf import FPDF
import markdown
import av
import numpy as np
from dotenv import load_dotenv

from sentinel.orchestrator import SentinelOrchestrator

try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False

if "sentinel" not in st.session_state:
    st.session_state.sentinel = None

st.set_page_config(page_title="HireMind Interviewer", page_icon=None, layout="wide")

st.markdown("""
<style>
    /* Styling to make text pop more */
    .stChatMessage { padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1rem; }
    h1 { color: #8b5cf6; }
</style>
""", unsafe_allow_html=True)

# Preset roles
PRESETS = {
    "Software Engineer": {
        "jd": "**Software Engineer** responsible for building scalable backend systems in Python/Go, designing REST APIs, and optimizing database performance in PostgreSQL.",
        "competencies": "System Design, API Design, Data Modeling, Debugging, Problem Solving"
    },
    "ML Engineer": {
        "jd": "**Machine Learning Engineer** focused on training and deploying deep learning models, optimizing inference pipelines, and managing model lifecycle with tools like PyTorch and MLflow.",
        "competencies": "Model Architecture, MLOps, Model Deployment, Debugging, Communication"
    },
    "App Developer": {
        "jd": "**Mobile App Developer** creating responsive, accessible cross-platform applications using React Native or Flutter. Strong focus on UI/UX and state management.",
        "competencies": "State Management, UI/UX Implementation, Optimization, Testing, Ownership"
    }
}

# Initialize session state for config
for key in ["jd", "competencies", "candidate_name", "api_key"]:
    if key not in st.session_state:
        st.session_state[key] = ""

def set_preset(role):
    st.session_state.jd = PRESETS[role]["jd"]
    st.session_state.competencies = PRESETS[role]["competencies"]

st.sidebar.title("HireMind Config")
st.sidebar.markdown("---")


st.session_state.api_key = os.getenv("GROQ_API")
st.sidebar.markdown("### Quick Presets")
cols = st.sidebar.columns(3)
if cols[0].button("Software Eng"): set_preset("Software Engineer")
if cols[1].button("ML Engineer"): set_preset("ML Engineer")
if cols[2].button("App Dev"): set_preset("App Developer")

st.sidebar.markdown("### Manual Config")
st.session_state.candidate_name = st.sidebar.text_input("Candidate Name", value=st.session_state.candidate_name, placeholder="e.g. Alice Smith")
st.session_state.jd = st.sidebar.text_area("Job Description", value=st.session_state.jd, height=120)
st.session_state.competencies = st.sidebar.text_input("Competencies", value=st.session_state.competencies, help="Comma separated list of skills to test.")

experience_tier = st.sidebar.selectbox(
    "Experience Level",
    ["Fresher", "Junior", "Mid-level", "Senior", "Principal/Staff"],
    key="experience_tier"
)

st.sidebar.markdown("---")

if "started" not in st.session_state:
    st.session_state.started = False
if "messages" not in st.session_state:
    st.session_state.messages = []

col1, col2 = st.sidebar.columns(2)
if col1.button("Start Interview", type="primary", use_container_width=True):
    if not st.session_state.api_key:
        st.sidebar.error("Please provide a Groq API Key.")
    elif not st.session_state.jd or not st.session_state.competencies:
        st.sidebar.error("Please provide JD and Competencies.")
    else:
        st.session_state.started = True
        st.session_state.messages = []
        st.session_state.sentinel = SentinelOrchestrator()
        if WEBRTC_AVAILABLE:
            st.session_state.sentinel.enable_webrtc_mode()
        st.session_state.sentinel.on_session_start(
            candidate_name=st.session_state.candidate_name,
            experience_tier=st.session_state.experience_tier
        )
        st.rerun()

if col2.button("End Session", use_container_width=True):
    st.session_state.started = False
    st.session_state.messages = []
    st.rerun()

st.title(" HireMind: High-Signal Interviewer")

if not st.session_state.started:
    st.info("Please configure the interview settings in the sidebar or select a preset, provide your Groq API Key, and click **Start Interview**.")
    st.divider()
    st.markdown("### How it works\n1. Enters a multi-phase internal loop to assess candidates.\n2. **Routes dynamically** based on depth.\n3. Generates a comprehensive final report.\n4. Keeps internal scoring hidden from the chat interface.")
else:
    # ─── MONITORING LAYOUT ────────────────────────────────────
    # Create main layout with video feed prominent + monitoring stats
    
    col_main, col_sidebar_monitoring = st.columns([2, 1])
    
    with col_sidebar_monitoring:
        st.markdown("### Monitoring Status")
        if st.session_state.sentinel:
            sentinel_obj = st.session_state.sentinel
            # Display monitoring indicators
            if sentinel_obj.video_monitor:
                st.metric("Video Feed", "Active", "OK")
            if sentinel_obj.audio_monitor:
                st.metric("Audio Stream", "Active", "OK")
    
    # ─── SENTINEL Camera Feed in Main Area ────────────────────────────────
    if WEBRTC_AVAILABLE and st.session_state.sentinel:
        sentinel_obj = st.session_state.sentinel

        def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
            """Process each video frame through SENTINEL's VideoMonitor."""
            img = frame.to_ndarray(format="bgr24")
            try:
                annotated = sentinel_obj.video_monitor.process_frame(img)
            except Exception:
                annotated = img
            return av.VideoFrame.from_ndarray(annotated, format="bgr24")

        def audio_frame_callback(frame: av.AudioFrame) -> av.AudioFrame:
            """Process each audio frame through SENTINEL's AudioMonitor."""
            try:
                audio_array = frame.to_ndarray()
                sentinel_obj.audio_monitor.process_audio_frames(
                    audio_array, frame.sample_rate
                )
            except Exception:
                pass
            return frame

        with col_main:
            st.markdown("### Live Interview Monitoring")
            webrtc_streamer(
                key="sentinel-cam",
                mode=WebRtcMode.SENDRECV,
                video_frame_callback=video_frame_callback,
                audio_frame_callback=audio_frame_callback,
                rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                media_stream_constraints={"video": True, "audio": True},
                async_processing=True,
            )
            st.caption("Camera feed showing eye tracking and facial analysis")
    
    # ─── Audio Monitoring & Heatmap ────────────────────────────
    st.markdown("---")
    st.markdown("### Audio Activity Monitoring")
    
    if st.session_state.sentinel and hasattr(st.session_state.sentinel, 'audio_monitor'):
        audio_monitor = st.session_state.sentinel.audio_monitor
        
        # Create placeholder for real-time audio energy visualization
        audio_plot_placeholder = st.empty()
        
        # Create monitoring state
        if "audio_visualization_data" not in st.session_state:
            st.session_state.audio_visualization_data = {
                "timestamps": [],
                "energy": [],
                "is_speech": []
            }
        
        # Display audio stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info("Voice Activity Detection: Active")
        with col2:
            st.info("Audio Energy: Monitoring")
        with col3:
            st.info("Sample Rate: 16kHz")
        
        st.caption("Real-time audio energy and VAD (Voice Activity Detection) visualization will appear here during the interview")
    
    # ─── End Audio Monitoring ──────────────────────────────────
    st.markdown("---")
    
    system_prompt = f"""You are HireMind, a high-signal AI interviewer specialized in detecting conceptual mastery — not vocabulary performance.

You will conduct a structured interview using the Job Description and Competency List provided below. You operate as a three-phase agent in a single session: Interviewer → Depth Evaluator → Report Generator.

═══════════════════════════════════════
CONFIGURATION
═══════════════════════════════════════
JD: {st.session_state.jd}
COMPETENCIES: {st.session_state.competencies}
CANDIDATE NAME: {st.session_state.candidate_name}
═══════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 1 — INTERVIEWER PERSONA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Persona: Professional, objective, and unflinching. You are not a friend or a coach. You do not telegraph scoring. You do not give encouragement mid-interview. You are a black box until the final report.

Interview flow:
- Greet the candidate in 1–2 sentences. Then immediately ask your first question targeting Competency #1.
- Ask one question at a time. Never ask multiple questions in a single turn.
- Questions must probe the HOW and WHY — not the WHAT. Bad: "Do you know what a load balancer is?" Good: "Walk me through how you'd decide between a layer-4 and layer-7 load balancer for a real-time chat product."
- After each candidate response, run Phase 2 internally before generating your next output.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 2 — DEPTH EVALUATOR (run silently after every candidate response)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classify the response against the current competency using exactly one of three labels:
SURFACE — Candidate used technical vocabulary but could not explain the underlying mechanism, trade-off, or reason.
PARTIAL — Candidate demonstrated foundational understanding but missed a critical nuance, edge case, or real-world constraint.
DEEP — Candidate explained the mechanism, named trade-offs, gave a structured example from experience, or reasoned about failure modes and alternatives.

Routing rules:
- DEEP → Advance to the next competency. Acknowledge in one sentence, then pivot.
- PARTIAL → Ask exactly one follow-up on the gap.
- SURFACE → Ask one Socratic probe.
- After two follow-ups on the same competency, force advance to the next competency.

Internal monologue formatting (MANDATORY):
You must output your internal monologue wrapped inside <thought>...</thought> tags, using this exact format:
<thought>
[DEPTH: surface/partial/deep | REASON: one sentence | ACTION: follow-up / advance]
</thought>
(The UI hides `thought` tags from the user, ensuring the black-box persona constraint).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHASE 3 — REPORT GENERATOR (trigger when all competencies are covered)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Close the interview with: "That covers everything I wanted to explore today. Thank you for your time." Then immediately generate the report below. Do not ask the candidate if they have questions.

Output this exact structure:

────────────────────────────────────────
HIREMIND EVALUATION REPORT
────────────────────────────────────────
Candidate: [name]
Role: [job title from JD]
Date: [today's date]

OVERALL SIGNAL
[2–3 sentences...]

COMPETENCY SCORES
For each competency:
  ▸ [Competency Name] — Score: X/5
    Evidence: [...]
    Gap: [...]

Score key:
  5 = Deep, 4 = Solid, 3 = Functional, 2 = Surface, 1 = No signal

HIRE SIGNAL
[Strong Yes / Yes / Lean Yes / Lean No / No]
[One sentence.]

CANDIDATE FEEDBACK
[3 tips...]
────────────────────────────────────────
>>>>>>> Stashed changes
"""

import json, time, threading, base64, hashlib, math, os, re
from datetime import datetime
from collections import deque
from flask import Flask, request, jsonify, Response, send_from_directory
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'proctorsense-secret-2026'

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), 'screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# ══════════════════════════════════════════════════════════════
#  DETECTION THRESHOLDS  (single source of truth)
# ══════════════════════════════════════════════════════════════
GAZE_THRESHOLD   = 0.35   # √(gx²+gy²) must exceed this to flag
NECK_THRESHOLD   = 20.0   # absolute degrees must exceed this to flag
FLAG_COOLDOWN_S  = 8      # seconds between same-type flags (throttle)

# ══════════════════════════════════════════════════════════════
#  CLEANUP ON STARTUP
# ══════════════════════════════════════════════════════════════
def cleanup_old_screenshots():
    """Delete ALL files in screenshots/ when the app starts."""
    removed = 0
    try:
        for fn in os.listdir(SCREENSHOTS_DIR):
            fp = os.path.join(SCREENSHOTS_DIR, fn)
            if os.path.isfile(fp):
                os.remove(fp)
                removed += 1
        print(f"[Startup] Cleaned {removed} old screenshot file(s) from {SCREENSHOTS_DIR}")
    except Exception as e:
        print(f"[Startup] Error cleaning screenshots: {e}")

# Run cleanup BEFORE creating the session
cleanup_old_screenshots()


# ══════════════════════════════════════════════════════════════
#  SHARED SESSION STATE  (one candidate session for demo)
# ══════════════════════════════════════════════════════════════
class CandidateSession:
    def __init__(self, candidate_id='CS-2047'):
        self.candidate_id = candidate_id
        self.started_at = datetime.now()
        self.lock = threading.Lock()

        # Monitoring state
        self.is_monitoring = True

        # Rolling feature window for Isolation Forest
        self.feature_window = deque(maxlen=200)
        self.model = IsolationForest(n_estimators=100, contamination=0.08,
                                     random_state=42, warm_start=False)
        self.scaler = StandardScaler()
        self.model_fitted = False

        # Current feature vector
        self.features = {
            'gaze_x': 0.0,
            'gaze_y': 0.0,
            'neck_angle': 0.0,
            'blink_rate': 15.0,
            'face_confidence': 1.0,
            'voice_energy': 0.0,
            'voice_is_speech': 0,
            'voice_duration': 0.0,
            'paste_count': 0,
            'type_velocity': 0.0,
            'answer_similarity': 0.0,
            'tab_switches': 0,
        }

        # Anomaly scores per channel
        self.scores = {
            'eye': 0.0,
            'neck': 0.0,
            'voice': 0.0,
            'iso_forest': 0.0,
            'text_paste': 0.0,
            'typing_velocity': 0.0,
            'overall': 0.0,
        }

        # Flags & evidence
        self.flags = []
        # screenshots list: only records where has_image=True (actual PNG saved)
        self.screenshots = []
        self.event_log = []

        # SSE subscribers
        self.subscribers = []

        # Voice state
        self.speech_start = None
        self.voice_event_count = 0
        self.consecutive_speech_frames = 0

        # Text state
        self.answer_history = {}
        self.paste_events = 0
        self.known_solutions = self._load_solution_fingerprints()

        # Background worker
        self._stop = False
        self.worker = threading.Thread(target=self._background_worker, daemon=True)
        self.worker.start()

    # ── Solution fingerprints ─────────────────────────────────
    def _load_solution_fingerprints(self):
        return [
            "hashmap seen complement target nums",
            "dict enumerate for i val in nums",
            "hash_map seen.get return i j",
            "OrderedDict move_to_end popitem last",
            "doubly linked list dummy head tail",
            "cache capacity self.cache OrderedDict",
            "token bucket sliding window redis lua",
            "leaky bucket fixed window counter expire",
            "rate_limit decorator middleware throttle",
            "atomicity consistency isolation durability",
            "basically available soft state eventual consistency",
        ]

    def _text_anomaly_score(self, text):
        if not text or len(text) < 20:
            return 0.0
        words = set(re.findall(r'\w+', text.lower()))
        max_sim = 0.0
        for sol in self.known_solutions:
            sol_words = set(sol.split())
            if not sol_words:
                continue
            sim = len(words & sol_words) / len(sol_words)
            max_sim = max(max_sim, sim)
        return min(1.0, max_sim)

    # ── Face update ───────────────────────────────────────────
    def update_face(self, data):
        """Called when frontend sends face landmark data."""
        if not self.is_monitoring:
            return
        with self.lock:
            self.features['gaze_x']         = float(data.get('gaze_x', 0))
            self.features['gaze_y']         = float(data.get('gaze_y', 0))
            self.features['neck_angle']     = float(data.get('neck_angle', 0))
            self.features['blink_rate']     = float(data.get('blink_rate', 15))
            self.features['face_confidence']= float(data.get('face_confidence', 1))

            gaze_dev = math.sqrt(self.features['gaze_x']**2 + self.features['gaze_y']**2)
            self.scores['eye']  = min(100, gaze_dev * 120)
            neck_dev = abs(self.features['neck_angle']) / 45.0
            self.scores['neck'] = min(100, neck_dev * 100)

            # ── Flag: gaze ───────────────────────────────────
            # Screenshot is captured by the FRONTEND when it receives this flag via SSE.
            # Backend only records the flag; it does NOT create its own screenshot record here.
            if gaze_dev > GAZE_THRESHOLD:
                direction = self._gaze_direction()
                self._maybe_flag(
                    f"Gaze deviation: looking {direction} (dev={gaze_dev:.2f})",
                    'warn', 'gaze'
                )

            # ── Flag: neck ───────────────────────────────────
            if abs(self.features['neck_angle']) > NECK_THRESHOLD:
                self._maybe_flag(
                    f"Neck tilt: {self.features['neck_angle']:.1f}°",
                    'warn', 'neck'
                )

            self._run_isolation_forest()
            self._emit_state()

    # ── Voice update ──────────────────────────────────────────
    def update_voice(self, data):
        """Called when frontend sends voice/VAD data.
        Voice anomalies are FLAGGED but NO screenshot is taken."""
        if not self.is_monitoring:
            return
        with self.lock:
            energy    = float(data.get('energy', 0))
            is_speech = bool(data.get('is_speech', False))
            self.features['voice_energy']    = energy
            self.features['voice_is_speech'] = 1 if is_speech else 0

            if is_speech:
                self.consecutive_speech_frames += 1
                if self.speech_start is None:
                    self.speech_start = time.time()
                self.features['voice_duration'] = time.time() - self.speech_start
            else:
                if self.consecutive_speech_frames > 3:
                    self.voice_event_count += 1
                    duration   = self.features['voice_duration']
                    score_boost = min(60, duration * 15)
                    self.scores['voice'] = min(100, self.scores['voice'] + score_boost)
                    severity   = 'bad' if duration > 3 else 'warn'
                    # take_screenshot=False — voice never gets a screenshot
                    self._maybe_flag(
                        f"Voice anomaly: speech #{self.voice_event_count} for {duration:.1f}s",
                        severity, 'voice', take_screenshot=False
                    )
                self.consecutive_speech_frames = 0
                self.speech_start = None
                self.features['voice_duration'] = 0.0
                self.scores['voice'] = max(0, self.scores['voice'] * 0.97)

            voice_score = energy * 80 + (20 if is_speech else 0)
            self.scores['voice'] = min(100, max(self.scores['voice'], voice_score))

            self._run_isolation_forest()
            self._emit_state()

    # ── Text / paste update ───────────────────────────────────
    def update_text(self, data):
        """Called on paste or typing burst — logged only, never flagged."""
        if not self.is_monitoring:
            return
        with self.lock:
            q_num      = data.get('q_num', 0)
            event_type = data.get('type', 'key')
            text       = data.get('text', '')
            char_delta = int(data.get('char_delta', 0))
            dt_ms      = float(data.get('dt_ms', 100))

            if event_type == 'paste':
                self.paste_events += 1
                self.features['paste_count'] = self.paste_events
                self.scores['text_paste']    = min(100, self.paste_events * 25)
                sim = self._text_anomaly_score(text)
                self.features['answer_similarity'] = sim
                self.scores['typing_velocity']     = min(100, sim * 100)
                self.event_log.append({
                    'level': 'info',
                    'msg':   f"PASTE on Q{q_num}: {len(text)} chars, similarity={sim*100:.0f}%",
                    'time':  datetime.now().strftime('%H:%M:%S'),
                })

            elif event_type == 'burst':
                velocity = (char_delta / max(dt_ms, 1)) * 1000
                self.features['type_velocity'] = velocity
                self.scores['typing_velocity'] = min(100, velocity * 2)
                if velocity > 30:
                    self.event_log.append({
                        'level': 'info',
                        'msg':   f"Q{q_num}: Typing burst {velocity:.0f} chars/s",
                        'time':  datetime.now().strftime('%H:%M:%S'),
                    })

            elif event_type == 'tab_switch':
                self.features['tab_switches'] += 1
                self.event_log.append({
                    'level': 'info',
                    'msg':   f"Tab/window switch #{int(self.features['tab_switches'])} detected",
                    'time':  datetime.now().strftime('%H:%M:%S'),
                })

            self._run_isolation_forest()
            self._emit_state()

    # ── Gaze direction helper ─────────────────────────────────
    def _gaze_direction(self):
        gx, gy = self.features['gaze_x'], self.features['gaze_y']
        if abs(gx) > abs(gy):
            return 'left' if gx < 0 else 'right'
        return 'up' if gy < 0 else 'down'

    # ── Isolation Forest ──────────────────────────────────────
    def _run_isolation_forest(self):
        fv = np.array([
            self.features['gaze_x'],
            self.features['gaze_y'],
            self.features['neck_angle'] / 45.0,
            (self.features['blink_rate'] - 15) / 10.0,
            1.0 - self.features['face_confidence'],
            self.features['voice_energy'],
            float(self.features['voice_is_speech']),
            self.features['voice_duration'] / 10.0,
            self.features['paste_count'] / 5.0,
            self.features['type_velocity'] / 50.0,
            self.features['answer_similarity'],
            self.features['tab_switches'] / 5.0,
        ], dtype=np.float32)

        self.feature_window.append(fv.copy())
        if len(self.feature_window) < 10:
            return

        X = np.array(list(self.feature_window))
        try:
            X_scaled    = self.scaler.fit_transform(X)
            self.model.fit(X_scaled)
            latest      = X_scaled[-1:].reshape(1, -1)
            raw_score   = self.model.decision_function(latest)[0]
            iso_pct     = max(0.0, min(100.0, (0.3 - raw_score) * 200))
            self.scores['iso_forest'] = iso_pct
            self.model_fitted = True
        except Exception:
            pass

        w = {'eye': 0.20, 'neck': 0.10, 'voice': 0.20,
             'iso_forest': 0.25, 'text_paste': 0.15, 'typing_velocity': 0.10}
        self.scores['overall'] = min(100, sum(self.scores.get(k, 0) * v for k, v in w.items()))

    # ── Flag throttle ─────────────────────────────────────────
    def _maybe_flag(self, msg, severity, flag_type, take_screenshot=True):
        """
        Raise a flag at most once per FLAG_COOLDOWN_S seconds per type.
        For 'gaze' and 'neck', take_screenshot=True causes the backend to
        emit a 'needs_screenshot' SSE event; the frontend captures the actual
        canvas frame and POSTs it to /api/screenshot.
        For 'voice', take_screenshot must always be False.
        """
        now = time.time()
        for f in self.flags:
            if f['type'] == flag_type and (now - f['ts']) < FLAG_COOLDOWN_S:
                return  # throttled

        flag = {
            'id':       len(self.flags),
            'msg':      msg,
            'severity': severity,
            'type':     flag_type,
            'ts':       now,
            'time_str': datetime.now().strftime('%H:%M:%S'),
            # Tell frontend whether it should capture a screenshot
            'needs_screenshot': take_screenshot and flag_type in ('gaze', 'neck'),
        }
        self.flags.append(flag)
        self.event_log.append({
            'level': 'bad' if severity == 'bad' else 'warn',
            'msg':   msg,
            'time':  datetime.now().strftime('%H:%M:%S'),
        })
        self._emit_event('flag', flag)

    # ── Save actual PNG from frontend ─────────────────────────
    def save_frame_screenshot(self, candidate_id, image_b64, meta):
        """
        Called from POST /api/screenshot.
        Saves the base64 PNG sent by the frontend canvas capture.
        Only gaze and neck types should ever reach this endpoint.
        """
        ts      = datetime.now()
        ss_type = meta.get('type', 'frame')

        # Safety: never save voice screenshots
        if ss_type == 'voice':
            return {'id': 'rejected', 'has_image': False}

        ss_id   = f"frame_{len(self.screenshots):04d}_{ss_type}_{ts.strftime('%H%M%S')}"
        img_path = None
        img_size = 0

        try:
            img_data  = image_b64.split(',')[1] if ',' in image_b64 else image_b64
            img_bytes = base64.b64decode(img_data)
            img_size  = len(img_bytes)

            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            img_path = os.path.join(SCREENSHOTS_DIR, f"{ss_id}.png")
            with open(img_path, 'wb') as f:
                f.write(img_bytes)

            if not os.path.exists(img_path) or os.path.getsize(img_path) == 0:
                raise IOError(f"File write failed: {img_path}")

            print(f"[Screenshot] Saved {img_path} ({img_size//1024} KB)")
        except Exception as e:
            self.event_log.append({
                'level': 'error',
                'msg':   f"Screenshot save error ({ss_type}): {str(e)}",
                'time':  datetime.now().strftime('%H:%M:%S'),
            })
            img_path = None

        record = {
            'id':           ss_id,
            'type':         ss_type,
            'severity':     meta.get('severity', 'warn'),
            'desc':         meta.get('desc', 'Anomaly frame'),
            'time':         ts.strftime('%H:%M:%S'),
            'ts':           ts.isoformat(),
            'has_image':    img_path is not None,
            'img_filename': f"{ss_id}.png" if img_path else None,
            'img_size_kb':  img_size // 1024 if img_size > 0 else 0,
            'scores_snapshot': dict(self.scores),
        }

        # Save companion JSON metadata
        try:
            meta_path = os.path.join(SCREENSHOTS_DIR, f"{ss_id}_meta.json")
            with open(meta_path, 'w') as f:
                json.dump(record, f, indent=2)
        except Exception as e:
            print(f"[Screenshot] Metadata save error: {e}")

        self.screenshots.append(record)
        self._emit_event('screenshot', record)
        return record

    # ── Background worker ─────────────────────────────────────
    def _background_worker(self):
        while not self._stop:
            time.sleep(2)
            with self.lock:
                if len(self.feature_window) >= 10:
                    self._run_isolation_forest()
                self.event_log.append({
                    'level': 'info',
                    'msg':   f"[Heartbeat] IF={self.scores['iso_forest']:.1f} overall={self.scores['overall']:.1f}",
                    'time':  datetime.now().strftime('%H:%M:%S'),
                })
                self._emit_state()

    # ── SSE helpers ───────────────────────────────────────────
    def _emit_state(self):
        payload = {
            'scores':           dict(self.scores),
            'features':         dict(self.features),
            'flag_count':       len(self.flags),
            'screenshot_count': len(self.screenshots),
            'voice_events':     self.voice_event_count,
            'paste_events':     self.paste_events,
            'model_fitted':     self.model_fitted,
            'timestamp':        datetime.now().isoformat(),
        }
        self._emit_event('state', payload)

    def _emit_event(self, event_type, data):
        msg  = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead = []
        for q in self.subscribers:
            try:
<<<<<<< Updated upstream
                q.append(msg)
            except Exception:
                dead.append(q)
        for q in dead:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass
=======
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=st.session_state.messages,
                    temperature=0.4,
                    max_tokens=1024,
                )
                initial_msg = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": initial_msg})
            except Exception as e:
                st.error(f"Error calling Groq API: {e}")
                st.stop()
    
    # Display chat
    report_found = False
    report_content = ""

    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        
        display_content = clean_text(msg["content"])
        with st.chat_message(msg["role"]):
            st.markdown(display_content)
        
        if "HIREMIND EVALUATION REPORT" in display_content:
            report_found = True
            report_content = display_content

    if report_found:
        st.success("Interview completed. The report has been generated.")
        pdf_data = generate_pdf(report_content)
        st.download_button(
            label="Download Assessment Report (PDF)",
            data=pdf_data,
            file_name="HireMind_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    if prompt := st.chat_input("Your response..."):
        if report_found:
            st.warning("The interview has already concluded. Please click 'End Session' or 'Start Interview' to begin a new one.")
            st.stop()

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            try:
                # Use streaming for real-time feel
                stream = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=st.session_state.messages,
                    temperature=0.4,
                    max_tokens=2048,
                    stream=True
                )
                full_response = ""
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        display_text = clean_text(full_response)
                        message_placeholder.markdown(display_text + "▌")
                
                final_text = clean_text(full_response)
                message_placeholder.markdown(final_text)
                
                st.session_state.messages.append({"role": "assistant", "content": full_response})

                if st.session_state.sentinel and len(st.session_state.messages) >= 2:
                    last_user_msg = next(
                        (m["content"] for m in reversed(st.session_state.messages)
                         if m["role"] == "user"), ""
                    )
                    st.session_state.sentinel.on_turn(
                        question=last_user_msg,
                        response=full_response
                    )

                if "HIREMIND EVALUATION REPORT" in final_text:
                    if st.session_state.sentinel:
                        report_path = st.session_state.sentinel.on_session_end()
                        # report_path available for download
                    st.rerun() # Refresh to show the PDF download above the input
>>>>>>> Stashed changes

    # ── Report ────────────────────────────────────────────────
    def get_report(self):
        with self.lock:
            flag_by_type = {}
            for f in self.flags:
                flag_by_type[f['type']] = flag_by_type.get(f['type'], 0) + 1

            # Only include screenshots where an actual image was saved
            confirmed_screenshots = [s for s in self.screenshots if s.get('has_image')]

            return {
                'candidate_id': self.candidate_id,
                'started_at':   self.started_at.isoformat(),
                'ended_at':     datetime.now().isoformat(),
                'is_monitoring': self.is_monitoring,
                'scores':       dict(self.scores),
                'flags':        list(self.flags),
                'screenshots':  confirmed_screenshots,
                'event_log':    list(self.event_log[-100:]),
                'features':     dict(self.features),
                'model_fitted': self.model_fitted,
                'summary': {
                    'total_flags':      len(self.flags),
                    'gaze_deviations':  flag_by_type.get('gaze', 0),
                    'neck_anomalies':   flag_by_type.get('neck', 0),
                    'voice_events':     self.voice_event_count,
                    'paste_events':     self.paste_events,
                    'tab_switches':     int(self.features['tab_switches']),
                    'screenshots_saved': len(confirmed_screenshots),
                    'flags_by_type':    flag_by_type,
                    'thresholds_used': {
                        'gaze_threshold':  GAZE_THRESHOLD,
                        'neck_threshold':  f"{NECK_THRESHOLD}°",
                        'flag_cooldown_s': FLAG_COOLDOWN_S,
                    },
                },
            }


# ══════════════════════════════════════════════════════════════
#  GLOBAL SESSION
# ══════════════════════════════════════════════════════════════
session = CandidateSession()


# ══════════════════════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    return send_from_directory(SCREENSHOTS_DIR, filename)

# ── SSE stream ──────────────────────────────────────────────
@app.route('/api/stream')
def stream():
    q = []
    session.subscribers.append(q)

    def generate():
        yield f"event: connected\ndata: {json.dumps({'status':'ok','candidate':session.candidate_id})}\n\n"
        while True:
            if q:
                yield q.pop(0)
            else:
                yield ": ping\n\n"
                time.sleep(0.5)

    return Response(generate(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no',
                        'Access-Control-Allow-Origin': '*',
                    })

# ── Face data ────────────────────────────────────────────────
@app.route('/api/face', methods=['POST', 'OPTIONS'])
def face():
    if request.method == 'OPTIONS':
        return _cors('')
    data = request.get_json(force=True)
    session.update_face(data)
    return _cors(jsonify({'ok': True}))

# ── Voice data ───────────────────────────────────────────────
@app.route('/api/voice', methods=['POST', 'OPTIONS'])
def voice():
    if request.method == 'OPTIONS':
        return _cors('')
    data = request.get_json(force=True)
    session.update_voice(data)
    return _cors(jsonify({'ok': True}))

# ── Text / keyboard data ─────────────────────────────────────
@app.route('/api/text', methods=['POST', 'OPTIONS'])
def text():
    if request.method == 'OPTIONS':
        return _cors('')
    data = request.get_json(force=True)
    session.update_text(data)
    return _cors(jsonify({'ok': True}))

# ── Screenshot upload from frontend canvas ───────────────────
@app.route('/api/screenshot', methods=['POST', 'OPTIONS'])
def screenshot():
    if request.method == 'OPTIONS':
        return _cors('')
    data      = request.get_json(force=True)
    image_b64 = data.get('image', '')
    meta      = data.get('meta', {})

    # Reject empty payloads
    if not image_b64:
        return _cors(jsonify({'ok': False, 'error': 'No image data'})), 400

    # Reject voice screenshots at the API level
    if meta.get('type') == 'voice':
        return _cors(jsonify({'ok': False, 'error': 'Voice screenshots are disabled'})), 400

    record = session.save_frame_screenshot(session.candidate_id, image_b64, meta)
    return _cors(jsonify({
        'ok':          True,
        'id':          record['id'],
        'has_image':   record.get('has_image', False),
        'filename':    record.get('img_filename'),
        'msg':         f"Screenshot saved: {record.get('img_filename', 'N/A')}",
    }))

# ── Full report ──────────────────────────────────────────────
@app.route('/api/report')
def report():
    return _cors(jsonify(session.get_report()))

# ── Submit exam ──────────────────────────────────────────────
@app.route('/api/submit', methods=['POST'])
def submit():
    session.is_monitoring = False
    session._emit_event('submitted', {
        'status':    'submitted',
        'timestamp': datetime.now().isoformat(),
        'message':   'Assessment submitted. Monitoring stopped.',
    })
    return _cors(jsonify({'ok': True, 'status': 'submitted'}))

# ── Reset session ────────────────────────────────────────────
@app.route('/api/reset', methods=['POST'])
def reset():
    global session
    cleanup_old_screenshots()
    session._stop = True
    session = CandidateSession()
    return _cors(jsonify({'ok': True}))

# ── List screenshots ─────────────────────────────────────────
@app.route('/api/screenshots')
def list_screenshots():
    files = []
    for fn in sorted(os.listdir(SCREENSHOTS_DIR)):
        if fn.endswith('.png'):
            files.append({'filename': fn, 'url': f'/screenshots/{fn}'})
    return _cors(jsonify({'screenshots': files}))

# ── CORS helper ──────────────────────────────────────────────
def _cors(resp):
    if isinstance(resp, str):
        resp = Response(resp, mimetype='text/plain')
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return resp


if __name__ == '__main__':
    print("=" * 60)
    print("  ProctorSense AI Backend")
    print(f"  Gaze threshold : {GAZE_THRESHOLD}  |  Neck threshold: {NECK_THRESHOLD}°")
    print(f"  Flag cooldown  : {FLAG_COOLDOWN_S}s")
    print("  Screenshots    : neck + eye ONLY (voice = flag only)")
    print("  http://localhost:5051")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5051, debug=False, threaded=True)
