import streamlit as st
from groq import Groq
import re
from fpdf import FPDF
import markdown

st.set_page_config(page_title="HireMind Interviewer", page_icon="🧠", layout="wide")

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

st.sidebar.title("🧠 HireMind Config")
st.sidebar.markdown("---")

# API Key input
api_key_input = st.sidebar.text_input("Groq API Key", type="password", value=st.session_state.api_key)
if api_key_input:
    st.session_state.api_key = api_key_input

st.sidebar.markdown("### ⚡ Quick Presets")
cols = st.sidebar.columns(3)
if cols[0].button("Software Eng"): set_preset("Software Engineer")
if cols[1].button("ML Engineer"): set_preset("ML Engineer")
if cols[2].button("App Dev"): set_preset("App Developer")

st.sidebar.markdown("### 📝 Manual Config")
st.session_state.candidate_name = st.sidebar.text_input("Candidate Name", value=st.session_state.candidate_name, placeholder="e.g. Alice Smith")
st.session_state.jd = st.sidebar.text_area("Job Description", value=st.session_state.jd, height=120)
st.session_state.competencies = st.sidebar.text_input("Competencies", value=st.session_state.competencies, help="Comma separated list of skills to test.")

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
        st.rerun()

if col2.button("End Session", use_container_width=True):
    st.session_state.started = False
    st.session_state.messages = []
    st.rerun()

st.title(" HireMind: High-Signal Interviewer")

if not st.session_state.started:
    st.info("👈 Please configure the interview settings in the sidebar or select a preset, provide your Groq API Key, and click **Start Interview**.")
    st.divider()
    st.markdown("### How it works\n1. Enters a multi-phase internal loop to assess candidates.\n2. **Routes dynamically** based on depth.\n3. Generates a comprehensive final report.\n4. Keeps internal scoring hidden from the chat interface.")
else:
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
"""

    client = Groq(api_key=st.session_state.api_key)

    def clean_text(text):
        # 1. Remove complete thought blocks
        text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
        # 2. Remove incomplete thought blocks at the end of the stream
        text = re.sub(r'<thought>.*', '', text, flags=re.DOTALL)
        # 3. Catch stray closing tags or open tags without angle brackets
        text = text.replace('</thought>', '')
        text = text.replace('<thought>', '')
        # 4. Remove any DEPTH formatting if tags were missed
        text = re.sub(r'\[DEPTH:.*?\]', '', text, flags=re.DOTALL)
        return text.strip()

    def generate_pdf(text):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=11)
            # Basic cleanup for unicode safety
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            # Render markdown into HTML for the PDF engine
            html = markdown.markdown(safe_text)
            pdf.write_html(html)
            
            out = pdf.output(dest='S')
            # Handle PyFPDF returning a string instead of bytearray
            if isinstance(out, str):
                return out.encode('latin-1', 'replace')
            return bytes(out)
        except Exception as e:
            # Fallback if markdown/html parsing fails
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=11)
            safe_text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 6, safe_text)
            out = pdf.output(dest='S')
            if isinstance(out, str):
                return out.encode('latin-1', 'replace')
            return bytes(out)

    if not st.session_state.messages:
        st.session_state.messages.append({"role": "system", "content": system_prompt})
        with st.spinner("Preparing interview..."):
            try:
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
        st.success("✅ Interview completed. The report has been generated.")
        pdf_data = generate_pdf(report_content)
        st.download_button(
            label="📄 Download Assessment Report (PDF)",
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
                
                if "HIREMIND EVALUATION REPORT" in final_text:
                    st.rerun() # Refresh to show the PDF download above the input

            except Exception as e:
                st.error(f"Error calling Groq API: {e}")
