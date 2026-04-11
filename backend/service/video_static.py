from pathlib import Path


class StaticExampleVideoService:
    def __init__(
        self,
        video_path: Path,
        *,
        audio_stub: bytes | None = None,
    ) -> None:
        self._video_path = video_path
        self._audio_stub = audio_stub if audio_stub is not None else b"\x00" * 2048

    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        _ = text
        return self._video_path.read_bytes(), self._audio_stub
