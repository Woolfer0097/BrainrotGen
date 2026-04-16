"""ElevenLabs API client for text-to-speech with timestamps.

Provides a simplified interface to the ElevenLabs API for generating
speech with word-level timing information used for subtitle generation.
"""

from elevenlabs.client import ElevenLabs
from elevenlabs.types.audio_with_timestamps_response import (
    AudioWithTimestampsResponse,
)

from backend.config import settings


class ElevenLabsClient:
    """Client for ElevenLabs text-to-speech API.

    Wraps the official ElevenLabs SDK with application-specific
    configuration and provides a simple interface for TTS with
    word-level timestamp alignment.
    """

    def __init__(self) -> None:
        """Initialize the client with API key from settings."""
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    def text_to_speech_with_timestamps(
        self, text: str
    ) -> AudioWithTimestampsResponse:
        """Convert text to speech with word-level timestamps.

        Args:
            text: The text to convert to speech (max 500 chars recommended).

        Returns:
            Response containing audio data and alignment timestamps.
        """
        return self.client.text_to_speech.convert_with_timestamps(
            voice_id=settings.voice_id,
            text=text,
            model_id=settings.model_id,
            output_format=settings.output_format,
        )
