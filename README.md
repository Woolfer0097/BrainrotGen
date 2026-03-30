# BrainrotGen

FastAPI backend and Streamlit web UI, Poetry, SQLite, SQLAlchemy.

## Project structure

```text
app/                         # entry shim: `uvicorn app.main:app` → re-exports `backend.main`
  main.py
backend/
  main.py                    # FastAPI `app`, routers, startup
  config.py
  api/v1/
    router.py
    endpoints/
      health.py
      items.py
      generate.py
db/
  connector.py               # engine, sessions, Base
  models/
  schemas/
web/
  app.py                     # Streamlit UI
utils/
  tts.py
```

## Quick start

```bash
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  

Streamlit (other terminal): `poetry run streamlit run web/app.py`
