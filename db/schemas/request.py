import datetime

from pydantic import BaseModel, Field


class RequestCreate(BaseModel):
    """Schema for creating a new video generation request.

    Attributes:
        login: User identifier for quota tracking.
        text: Text to convert to speech and display as subtitles.
        duration: Estimated duration of the generated video in seconds.
    """

    login: str = Field(..., description="User login for quota tracking")
    text: str = Field(..., description="Text content for TTS and subtitles")
    duration: int = Field(..., description="Estimated video duration in seconds")


class RequestRead(BaseModel):
    """Schema for reading a video generation request from the database.

    Attributes:
        id: Unique database identifier for the request.
        login: User identifier who made the request.
        date: UTC timestamp when the request was created.
        text: Text content that was processed.
        duration: Video duration in seconds (updated after processing).
    """

    id: int = Field(..., description="Unique request ID")
    login: str = Field(..., description="User login")
    date: datetime.datetime = Field(..., description="Request creation timestamp (UTC)")
    text: str = Field(..., description="Processed text content")
    duration: int = Field(..., description="Final video duration in seconds")
