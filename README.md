# BrainrotGen

FastAPI backend for generating "brainrot" videos - short-form content with TTS voiceover, subtitles, random background videos, and background music.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  Streamlit  │─────▶│   FastAPI    │─────▶│   SQLite    │
│    (UI)     │      │   Backend    │      │  Database   │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  ElevenLabs  │
                     │     TTS      │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │    FFmpeg    │
                     │ (composition)│
                     └──────────────┘
```

**Stack:** Python 3.11+, FastAPI, Streamlit, SQLAlchemy, SQLite, FFmpeg, ElevenLabs API

## Quick Start

1. **Prerequisites:**
   - Get an ElevenLabs API key
   - Unzip `media.zip` (contains background videos and music)
   - Install FFmpeg: `sudo apt install ffmpeg` (Ubuntu/Debian)

2. **Setup:**
   ```bash
   poetry install
   cp .env.example .env
   # Edit .env with your ElevenLabs API key
   ```

3. **Run the API:**
   ```bash
   poetry run uvicorn app.main:app --reload
   ```
   API docs available at: http://127.0.0.1:8000/docs

4. **Run the Web UI (in another terminal):**
   ```bash
   poetry run streamlit run web/app.py
   ```
   Access at: http://localhost:8501

## API Endpoints

### Health Check
```
GET /api/v1/health
```
Returns: `{"status": "ok"}`

### Generate Video
```
POST /api/v1/generate/
Content-Type: application/json

{
  "text": "Your text here (max 500 chars)",
  "login": "user_identifier"
}
```

**Response:** MP4 video file (`video/mp4`)

**Error Responses:**
- `429 Too Many Requests` - Daily quota exceeded (300 seconds/user/day)
- `500 Internal Server Error` - Video generation failed
- `504 Gateway Timeout` - Processing timed out (5 minutes)

### cURL Example
```bash
curl -X POST http://127.0.0.1:8000/api/v1/generate/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "login": "test_user"}' \
  --output video.mp4
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `ELEVENLABS_API_KEY` | (required) | Your ElevenLabs API key |
| `VOICE_ID` | - | ElevenLabs voice ID |
| `MODEL_ID` | `eleven_flash_v2_5` | TTS model |
| `OUTPUT_FORMAT` | `mp3_44100_128` | Audio format |
| `USE_STATIC_EXAMPLE_VIDEO` | `false` | Use static video for testing |
| `SQLITE_DB_PATH` | `./app.db` | Database file path |

## Performance Testing

Use static video mode to test without ElevenLabs API calls:

```bash
USE_STATIC_EXAMPLE_VIDEO=1 poetry run uvicorn app.main:app
locust -f tests/load_test.py
```

Access Locust UI at http://localhost:8089

## Project Structure

```
backend/
  api/v1/endpoints/     # API route handlers
  service/              # Business logic (video gen, quota, polling)
  clients/              # External API clients
  config.py             # Settings
  main.py               # FastAPI app
db/
  models/               # SQLAlchemy models
  schemas/              # Pydantic schemas
  connector.py          # Database setup
utils/                  # TTS utilities
web/                    # Streamlit frontend
tests/                  # Test suite
media/                  # Background videos and music
```
