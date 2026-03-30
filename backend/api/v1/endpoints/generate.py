from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.service import VideoGenerationError, VideoGenerationService

router = APIRouter(prefix="/generate", tags=["generate"])
video_service = VideoGenerationService()


class GenerateBody(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/")
def generate_video(body: GenerateBody) -> Response:
    try:
        video_bytes = video_service.generate(body.text)
    except VideoGenerationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Unexpected generation error: {exc}"
        ) from exc

    return Response(content=video_bytes, media_type="video/mp4")
