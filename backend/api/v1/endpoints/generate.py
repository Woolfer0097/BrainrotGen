import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.service import VideoGenerationError, VideoGenerationService
from backend.service.quota import DAILY_QUOTA_SECONDS, can_accept_request
from utils.tts import estimate_duration
from db.connector import SessionLocal
from db.models.request import Request as RequestModel

router = APIRouter(prefix="/generate", tags=["generate"])
video_service = VideoGenerationService()


class GenerateBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=25_000)
    login: str = Field(..., min_length=1, max_length=32)


@router.post("/")
def generate_video(body: GenerateBody) -> Response:
    login = body.login

    if not can_accept_request(login, body.text):
        raise HTTPException(
            status_code=429,
            detail=f"Daily quota exceeded ({DAILY_QUOTA_SECONDS}s limit)",
        )

    estimated = estimate_duration(body.text)
    now = datetime.datetime.now(datetime.timezone.utc)

    with SessionLocal() as db:
        db_request = RequestModel(
            login=login,
            date=now,
            text=body.text,
            duration=estimated,
        )
        db.add(db_request)
        db.commit()
        db.refresh(db_request)

    try:
        video_bytes = video_service.generate(body.text)
    except VideoGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected generation error: {exc}",
        ) from exc

    return Response(content=video_bytes, media_type="video/mp4")
