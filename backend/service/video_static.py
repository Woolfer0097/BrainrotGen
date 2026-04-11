"""Static video service for testing without ElevenLabs API calls.

Provides a mock implementation that returns a pre-recorded video file
instead of generating new videos. Useful for load testing and development.
"""

from pathlib import Path


class StaticExampleVideoService:
    """Service that returns a static video file for testing.

    Instead of generating videos via ElevenLabs and FFmpeg, this service
    returns a pre-recorded video file. Used for load testing and development
    to avoid API costs and processing time.

    Attributes:
        _video_path: Path to the static video file to return.
        _audio_stub: Dummy audio bytes (not real audio).
    """

    def __init__(
        self,
        video_path: Path,
        *,
        audio_stub: bytes | None = None,
    ) -> None:
        """Initialize with path to static video.

        Args:
            video_path: Path to the video file to return.
            audio_stub: Optional dummy audio bytes.
        """
        self._video_path = video_path
        self._audio_stub = (
            audio_stub if audio_stub is not None else b"\x00" * 2048
        )

    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        """Return the static video file (text parameter is ignored).

        Args:
            text: Ignored - only present for API compatibility.

        Returns:
            Tuple of (video_bytes, dummy_audio_bytes).
        """
        _ = text
        return self._video_path.read_bytes(), self._audio_stub
