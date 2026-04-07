import datetime
import json
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.service.poller import REQUEST_ARTIFACTS_DIR
from backend.service.poller_runtime import start_request_poller
from backend.service.quota import DAILY_QUOTA_SECONDS, can_accept_request
from db.connector import SessionLocal
from db.models.request import Request as RequestModel
from utils.tts import estimate_duration

router = APIRouter(prefix="/generate", tags=["generate"])

PROCESSING_TIMEOUT_SECONDS = 300.0
PROCESSING_CHECK_INTERVAL_SECONDS = 0.25


class GenerateBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)

    login: str = Field(..., min_length=1, max_length=32)


@router.post(
    "/",
    response_class=Response,
    responses={
        200: {
            "description": "Generated video",
            "content": {
                "video/mp4": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
def generate_video(body: GenerateBody) -> Response:
    start_request_poller()

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
            duration=int(estimated),
        )
        db.add(db_request)
        db.commit()
        db.refresh(db_request)

    request_id = int(db_request.id)
    expected_request_date = db_request.date.isoformat()
    video_bytes = _wait_for_processed_video(
        request_id=request_id,
        expected_request_date=expected_request_date,
        timeout_seconds=PROCESSING_TIMEOUT_SECONDS,
        interval_seconds=PROCESSING_CHECK_INTERVAL_SECONDS,
    )

    return Response(content=video_bytes, media_type="video/mp4")


def _wait_for_processed_video(
    *,
    request_id: int,
    expected_request_date: str,
    timeout_seconds: float,
    interval_seconds: float,
) -> bytes:
    request_dir = REQUEST_ARTIFACTS_DIR / str(request_id)
    video_path = request_dir / "video.mp4"
    meta_path = request_dir / "meta.json"
    deadline = time.monotonic() + max(0.1, timeout_seconds)

    while time.monotonic() < deadline:
        if meta_path.exists():
            meta = _read_meta(meta_path)
            if meta.get("request_date") != expected_request_date:
                time.sleep(max(0.05, interval_seconds))
                continue
            if meta.get("ok") is False:
                detail = str(meta.get("error") or "Video generation failed")
                raise HTTPException(status_code=500, detail=detail)
            if meta.get("ok") is True and video_path.exists():
                return video_path.read_bytes()

        time.sleep(max(0.05, interval_seconds))

    raise HTTPException(
        status_code=504,
        detail="Timed out waiting for poller to process request",
    )


def _read_meta(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return data
    return {}
