from elevenlabs.client import ElevenLabs

from backend.config import settings


class ElevenLabsClient:
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    def text_to_speech_with_timestamps(self, text: str):
        return self.client.text_to_speech.convert_with_timestamps(
            voice_id=settings.voice_id,
            text=text,
            model_id=settings.model_id,
            output_format=settings.output_format,
        )
