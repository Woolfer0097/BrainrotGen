# BrainrotGen

Simple FastAPI boilerplate using Poetry, SQLite, and SQLAlchemy.

## Project structure

```text
app/
  api/
    v1/
      endpoints/
  config.py
  main.py
db/
  connector.py
  models/
  schemas/
```

## Quick start

```bash
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs
