# Quick Start Guide: HireMind

Get the interview platform running in 5 minutes.

## 1️⃣ Configure API Keys (2 min)

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:
```bash
# Get from: https://console.groq.com/keys
GROQ_API=gsk_YOUR_KEY

# Get from: https://console.deepgram.com
DEEPGRAM_API_KEY=your_key

# Get from: https://console.cloud.google.com (create service account)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/google-service-account.json
GOOGLE_CLOUD_PROJECT=your-project-id
```

> **No API keys yet?** Use mock mode in development: `MOCK_MODE=true` (audio will be silent)

---

## 2️⃣ Start Backend (1 min)

```bash
cd backend
python -m venv venv
source venv/bin/activate              # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn main:app --reload
```

✅ Backend ready at `http://localhost:8000/docs` (API documentation)

---

## 3️⃣ Start Frontend (1 min)

Open new terminal:

```bash
cd frontend
npm install
npm run dev
```

✅ Frontend ready at `http://localhost:5173`

---

## 4️⃣ Run Interview (1 min)

1. Open http://localhost:5173
2. Select **Software Engineer** preset
3. Enter name: `Test User`
4. Click **Start Interview**
5. Listen to question → Record response → Submit
6. See next question appear automatically
7. Complete 3 turns → Get final report

---

## Using Docker (Alternative)

```bash
# Single command to start everything
docker-compose up

# In another terminal, check services
docker-compose ps
```

✅ Backend: `http://localhost:8000`
✅ Frontend: `http://localhost:5173`

---

## What Happens Behind the Scenes

```
You Record Response (WebM)
    ↓
Deepgram STT: Audio → Text transcript
    ↓
SENTINEL: Multimodal analysis (gaze, voice, content)
    ↓
Groq LLM: Evaluate depth + generate next question
    ↓
Google TTS: Question text → MP3 audio
    ↓
Frontend: Question plays, you respond, repeat
    ↓
After 3 questions: PDF report with scores
```

---

## API Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/interview/start` | POST | Start new interview session |
| `/api/interview/{id}/submit-response` | POST | Submit audio response |
| `/api/interview/{id}/audio/{turn}` | GET | Stream TTS audio for question |
| `/api/interview/{id}/end` | POST | End session and generate report |
| `/ws/interview/{id}` | WS | Real-time monitoring events |

See full docs at `http://localhost:8000/docs`

---

## Troubleshooting

**"Connection refused"** → Make sure both backend and frontend are running
**"Microphone denied"** → Click allow when browser asks for permission
**"No audio playing"** → Check Google TTS API key and browser console for errors
**"Empty responses"** → Check Groq API key and backend logs

```bash
# View backend logs
docker-compose logs -f backend

# Or if running locally:
tail -f backend.log
```

---

## Next Steps

- ✅ Complete test interview (see `TESTING_GUIDE.md`)
- ✅ Review deployment docs (`DEPLOYMENT.md`)
- ✅ Configure different role presets in `ConfigPanel.jsx`
- ✅ Customize competencies and JD
- ✅ Deploy to production with `docker-compose.prod.yml`

---

## Key Features

🎙️ **Voice I/O**: Deepgram STT + Google Cloud TTS  
📹 **Video Monitoring**: Real-time gaze, voice, content analysis  
🎯 **Smart Evaluation**: Groq LLM for depth assessment  
📊 **Integrity Dashboard**: Real-time monitoring scores  
🔒 **Security**: Multimodal fraud detection  
📄 **Reports**: Automatic PDF generation with scores  

---

## Support

- Backend API docs: `http://localhost:8000/docs`
- See `DEPLOYMENT.md` for detailed setup
- See `TESTING_GUIDE.md` for test scenarios
- Check backend logs: `docker-compose logs backend`

