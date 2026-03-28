from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateBody(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/")
def generate_video_placeholder(body: GenerateBody) -> JSONResponse:
    return JSONResponse(
        status_code=501,
        content={
            "detail": "Video generation is not implemented yet.",
            "text_length": len(body.text),
        },
    )
