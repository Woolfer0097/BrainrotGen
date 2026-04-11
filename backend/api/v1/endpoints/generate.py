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
    """Request body for video generation endpoint.

    Attributes:
        text: The text to convert to speech and display as subtitles.
            Must be between 1 and 500 characters.
        login: User identifier for quota tracking.
            Must be between 1 and 32 characters.
    """

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Text to convert to speech (1-500 characters)",
    )
    login: str = Field(
        ...,
        min_length=1,
        max_length=32,
        description="User login for quota tracking (1-32 characters)",
    )


@router.post(
    "/",
    response_class=Response,
    summary="Generate brainrot video",
    description=(
        "Generates a short-form 'brainrot' video with TTS voiceover, "
        "subtitles, random background video, and background music. "
        "Uses ElevenLabs for text-to-speech with word-level timestamps. "
        "Returns the generated MP4 video directly. "
        "Each user has a daily quota of 5 minutes of video generation."
    ),
    responses={
        200: {
            "description": "Generated MP4 video with subtitles and audio",
            "content": {
                "video/mp4": {"schema": {"type": "string", "format": "binary"}}
            },
        },
        429: {
            "description": "Daily quota exceeded (300 seconds limit per user)",
        },
        500: {"description": "Video generation failed"},
        504: {"description": "Request timed out waiting for processing"},
    },
)
def generate_video(body: GenerateBody) -> Response:
    """Generate a brainrot video from text.

    Args:
        body: The request body containing text and user login.

    Returns:
        A FastAPI Response containing the generated MP4 video bytes.

    Raises:
        HTTPException: 429 if daily quota exceeded.
        HTTPException: 500 if video generation fails.
        HTTPException: 504 if processing times out.
    """
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
    """Poll for video processing completion and return the result.

    Waits for the background poller to finish processing the request,
    checking periodically for completion or failure.

    Args:
        request_id: The database ID of the request being processed.
        expected_request_date: ISO format date string to verify request freshness.
        timeout_seconds: Maximum time to wait for processing.
        interval_seconds: Sleep interval between status checks.

    Returns:
        The generated video file as raw bytes.

    Raises:
        HTTPException: 500 if video generation failed.
        HTTPException: 504 if timeout exceeded.
    """
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
    """Read and parse a JSON metadata file.

    Args:
        path: Path to the JSON metadata file.

    Returns:
        Parsed JSON as a dictionary, or empty dict on error.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict):
        return data
    return {}
