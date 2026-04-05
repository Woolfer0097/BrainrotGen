# BrainrotGen

FastAPI backend and Streamlit web UI, Poetry, SQLite, SQLAlchemy.

## Project structure



## Quick start

1. Ask for API KEY of elevenlabs
2. Unzip media.zip

3. 
```bash
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs  

```bash
Streamlit (other terminal): `poetry run streamlit run web/app.py`
```

  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://172.18.0.1:8501
