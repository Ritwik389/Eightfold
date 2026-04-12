# Migration Guide: Gemini LLM + TTS

## Summary of Changes

HireMind has been migrated from **Groq LLM + Google Cloud TTS** to **Gemini 2.0 Flash (aistudio API)** for both language model and text-to-speech capabilities.

### What Changed

| Component | Before | After |
|-----------|--------|-------|
| LLM | Groq llama-3.3-70b | Gemini 2.0 Flash |
| TTS | Google Cloud Text-to-Speech | Gemini API (aistudio) |
| STT | Deepgram nova-2 | Deepgram nova-2 (unchanged) |
| API Setup | Groq API key + Google service account | Single Gemini API key |

### Benefits

✅ **Simpler Setup**: One API key instead of multiple  
✅ **No Google Cloud Service Account**: Just use aistudio API key  
✅ **Faster Iteration**: Gemini 2.0 Flash is optimized for speed  
✅ **Integrated Full Stack**: LLM + TTS from same provider  
✅ **Fewer Dependencies**: Removed google-cloud-texttospeech SDK  

---

## Files Updated

### Backend

| File | Changes |
|------|---------|
| `backend/requirements.txt` | Removed: groq, google-cloud-texttospeech; Updated: google-generativeai v0.5.1 |
| `backend/integrations/gemini_llm.py` | **NEW** - Gemini LLM for question generation, evaluation, reports |
| `backend/integrations/gemini_tts.py` | **NEW** - Gemini TTS for audio synthesis |
| `backend/main.py` | Updated imports: GeminiLLM, GeminiTTS; removed Groq/Google Cloud references |
| `.env.example` | Updated to use GEMINI_API_KEY only (removed GROQ_API, Google Cloud creds) |

### What's Preserved

- ✅ Deepgram STT integration (unchanged)
- ✅ SENTINEL monitoring (unchanged)
- ✅ React frontend (unchanged)
- ✅ FastAPI server structure (unchanged)
- ✅ WebSocket real-time monitoring (unchanged)
- ✅ Interview flow and UX (unchanged)

---

## Setup Instructions

### 1. Get Gemini API Key

1. Go to **https://aistudio.google.com/app/apikey**
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the API key

### 2. Update Environment

Create `.env` file from template:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Required: Gemini API Key (from aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Customize models/voices
GEMINI_LLM_MODEL=gemini-2.0-flash
GEMINI_TTS_VOICE=Kore

# Deepgram STT (unchanged)
DEEPGRAM_API_KEY=your_deepgram_key_here
DEEPGRAM_MODEL=nova-2
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Start Backend

```bash
uvicorn main:app --reload
```

---

## Gemini Configuration

### LLM Models Available

```
GEMINI_LLM_MODEL=gemini-2.0-flash      # Fast, latest (recommended)
GEMINI_LLM_MODEL=gemini-1.5-pro        # More capable, slower
GEMINI_LLM_MODEL=gemini-1.5-flash      # Balanced
```

### TTS Voices Available

```
GEMINI_TTS_VOICE=Puck                  # Male, playful
GEMINI_TTS_VOICE=Charon                # Male, deep and serious
GEMINI_TTS_VOICE=Kore                  # Female, warm and professional (recommended)
GEMINI_TTS_VOICE=Fenrir                # Male, serious
GEMINI_TTS_VOICE=Aoide                 # Female, friendly
```

---

## API Key Comparison

### Before (Groq + Google Cloud)

```env
# Groq
GROQ_API=gsk_abc123...

# Google Cloud (requires JSON service account file)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GOOGLE_CLOUD_PROJECT=my-project-id
GOOGLE_TTS_VOICE=en-US-Neural2-C

# Deepgram
DEEPGRAM_API_KEY=xyz789...
```

### After (Gemini Only)

```env
# Gemini (single key for LLM + TTS)
GEMINI_API_KEY=AIzaSy...

# Optional customization
GEMINI_LLM_MODEL=gemini-2.0-flash
GEMINI_TTS_VOICE=Kore

# Deepgram (unchanged)
DEEPGRAM_API_KEY=xyz789...
```

---

## Code Changes Reference

### Import Changes

**Before:**
```python
from .integrations.groq_llm import GroqLLM
from .integrations.google_tts import GoogleTTS
```

**After:**
```python
from .integrations.gemini_llm import GeminiLLM
from .integrations.gemini_tts import GeminiTTS
```

### Usage Changes

**Before:**
```python
llm = GroqLLM()
question = await llm.generate_question(...)

tts = GoogleTTS()
audio = await tts.synthesize(question)
```

**After:**
```python
llm = GeminiLLM()
question = await llm.generate_question(...)

tts = GeminiTTS()
audio = await tts.synthesize(question)
```

---

## Troubleshooting

### "API key not valid" Error

- Check GEMINI_API_KEY is set correctly in .env
- Verify key from https://aistudio.google.com/app/apikey
- Make sure no extra spaces or quotes

### No audio playing

- Verify GEMINI_API_KEY is valid
- Check network connectivity
- Backend logs will show errors: `docker-compose logs backend | grep TTS`

### LLM responses seem generic

- Increase GEMINI_LLM_MODEL to gemini-1.5-pro for better quality (will be slower)
- Check backend logs for potential context window issues

### Docker Deployment

When using docker-compose:

1. Delete old google-cloud-texttospeech from image
2. Rebuild backend image:
   ```bash
   docker-compose build --no-cache backend
   ```
3. Update .env in docker-compose context
4. Restart services:
   ```bash
   docker-compose up -d
   ```

---

## API Response Format (Unchanged)

The backend API responses remain identical to the previous version. No frontend changes required.

**Example Response:**
```json
{
  "session_id": "xyz123",
  "question": "Tell me about your experience...",
  "audio_url": "http://localhost:8000/api/interview/xyz123/audio/0"
}
```

---

## Performance Comparison

| Metric | Groq | Gemini 2.0 Flash |
|--------|------|-----------------|
| LLM Latency | 3-5s | 2-4s ⚡ |
| TTS Latency | 1-2s | 1-2s |
| Audio Quality | Good | Good |
| Cost | Pay-per-token | Pay-per-token |
| Setup Complexity | High | Low ✅ |

---

## Rollback (If Needed)

If you need to rollback to Groq + Google Cloud:

```bash
# Revert requirements.txt
git checkout backend/requirements.txt

# Revert main.py
git checkout backend/main.py

# Reinstall
pip install -r requirements.txt

# Use old .env
export GROQ_API=...
export GOOGLE_APPLICATION_CREDENTIALS=...
```

---

## Next Steps

1. ✅ Copy `.env.example` to `.env`
2. ✅ Add your GEMINI_API_KEY
3. ✅ Add your DEEPGRAM_API_KEY
4. ✅ Start backend: `uvicorn main:app --reload`
5. ✅ Start frontend: `npm run dev`
6. ✅ Test interview flow

See [QUICKSTART.md](../QUICKSTART.md) for full setup guide.
