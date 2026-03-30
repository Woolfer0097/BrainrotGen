from elevenlabs.client import ElevenLabs
from backend.config import settings


class ElevenLabsClient:
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key)

    def text_to_speech(self, text):
        self.client.text_to_speech.convert(
            text=text,
            voice_id=settings.voice_id,
            model_id=settings.model_id,
            output_format=settings.output_format,
        )
