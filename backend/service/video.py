import base64
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from backend.clients.elevenlabs_client import ElevenLabsClient
from backend.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MEDIA_DIR = PROJECT_ROOT / "media"
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}


@dataclass(frozen=True)
class TimedWord:
    text: str
    start_seconds: float
    end_seconds: float


class VideoGenerationError(RuntimeError):
    pass


class VideoGenerationService:
    SUBTITLE_STYLE = (
        "FontName=DejaVu Sans,"
        "FontSize=13,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&HAA000000,"
        "BackColour=&H66000000,"
        "BorderStyle=3,"
        "Outline=1,"
        "Shadow=0,"
        "Alignment=2,"
        "MarginV=120"
    )

    def __init__(
        self, elevenlabs_client: ElevenLabsClient | None = None
    ) -> None:
        self.elevenlabs_client = elevenlabs_client or ElevenLabsClient()

    def generate(self, text: str) -> bytes:
        video_bytes, _ = self._generate_with_audio(text)
        return video_bytes

    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        video_bytes, audio_bytes = self._generate_with_audio(text)
        return video_bytes, audio_bytes

    def _generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        response = self.elevenlabs_client.text_to_speech_with_timestamps(
            text=text
        )
        payload = self._to_dict(response)

        audio_bytes = self._decode_audio(payload)
        alignment = self._extract_alignment(payload)
        words = self._alignment_to_words(alignment)
        if not words:
            raise VideoGenerationError(
                "No timestamped words were returned by ElevenLabs"
            )

        cues = self._chunk_words(words)
        subtitles_srt = self._build_srt(cues)
        background_video = self._pick_random_video()

        with TemporaryDirectory(prefix="brainrotgen_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            audio_path = tmp_path / f"voice.{self._audio_extension()}"
            subtitles_path = tmp_path / "subtitles.srt"
            output_path = tmp_path / "brainrot_video.mp4"

            audio_path.write_bytes(audio_bytes)
            subtitles_path.write_text(subtitles_srt, encoding="utf-8")

            self._render_video(
                background_video=background_video,
                audio_path=audio_path,
                subtitles_path=subtitles_path,
                output_path=output_path,
            )

            return output_path.read_bytes(), audio_bytes

    @staticmethod
    def _to_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if hasattr(value, "dict"):
            return value.dict()
        raise VideoGenerationError("Unsupported ElevenLabs response format")

    @staticmethod
    def _decode_audio(payload: dict[str, Any]) -> bytes:
        audio_base64 = payload.get("audio_base_64") or payload.get(
            "audio_base64"
        )
        if not audio_base64:
            raise VideoGenerationError("Missing audio payload from ElevenLabs")

        try:
            return base64.b64decode(audio_base64, validate=True)
        except (ValueError, TypeError) as exc:
            raise VideoGenerationError(
                "Failed to decode ElevenLabs audio"
            ) from exc

    @staticmethod
    def _extract_alignment(payload: dict[str, Any]) -> dict[str, Any]:
        alignment = payload.get("normalized_alignment") or payload.get(
            "alignment"
        )
        if alignment is None:
            raise VideoGenerationError(
                "Missing alignment in ElevenLabs response"
            )

        if isinstance(alignment, dict):
            return alignment
        if hasattr(alignment, "model_dump"):
            return alignment.model_dump()
        if hasattr(alignment, "dict"):
            return alignment.dict()

        raise VideoGenerationError("Unsupported alignment payload format")

    @staticmethod
    def _alignment_to_words(alignment: dict[str, Any]) -> list[TimedWord]:
        characters = alignment.get("characters") or []
        starts = alignment.get("character_start_times_seconds") or []
        ends = alignment.get("character_end_times_seconds") or []

        if not (len(characters) == len(starts) == len(ends)):
            raise VideoGenerationError("Invalid alignment arrays length")

        words: list[TimedWord] = []
        buffer: list[str] = []
        word_start: float | None = None
        word_end: float | None = None

        for char, start, end in zip(characters, starts, ends):
            if char.isspace():
                if buffer and word_start is not None and word_end is not None:
                    words.append(
                        TimedWord(
                            text="".join(buffer),
                            start_seconds=word_start,
                            end_seconds=word_end,
                        )
                    )
                buffer = []
                word_start = None
                word_end = None
                continue

            if word_start is None:
                word_start = float(start)
            word_end = float(end)
            buffer.append(char)

        if buffer and word_start is not None and word_end is not None:
            words.append(
                TimedWord(
                    text="".join(buffer),
                    start_seconds=word_start,
                    end_seconds=word_end,
                )
            )

        return [word for word in words if word.text.strip()]

    @staticmethod
    def _chunk_words(
        words: list[TimedWord],
        max_words: int = 7,
        max_chars: int = 34,
        max_duration_seconds: float = 3.2,
    ) -> list[list[TimedWord]]:
        cues: list[list[TimedWord]] = []
        current: list[TimedWord] = []

        for word in words:
            if not current:
                current = [word]
                continue

            candidate = current + [word]
            candidate_text = " ".join(item.text for item in candidate)
            candidate_duration = word.end_seconds - current[0].start_seconds

            if (
                len(candidate) > max_words
                or len(candidate_text) > max_chars
                or candidate_duration > max_duration_seconds
            ):
                cues.append(current)
                current = [word]
            else:
                current = candidate

        if current:
            cues.append(current)

        return cues

    def _build_srt(self, cues: list[list[TimedWord]]) -> str:
        lines: list[str] = []

        for idx, cue in enumerate(cues, start=1):
            start_seconds = cue[0].start_seconds
            end_seconds = max(cue[-1].end_seconds, start_seconds + 0.35)
            text = " ".join(word.text for word in cue).strip()
            if not text:
                continue

            lines.append(str(idx))
            lines.append(
                f"{self._format_srt_timestamp(start_seconds)} --> "
                f"{self._format_srt_timestamp(end_seconds)}"
            )
            lines.append(text)
            lines.append("")

        if not lines:
            raise VideoGenerationError(
                "Failed to build subtitles from alignment"
            )

        return "\n".join(lines)

    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        total_ms = max(0, int(round(seconds * 1000)))
        hours, rem = divmod(total_ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        secs, ms = divmod(rem, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

    @staticmethod
    def _pick_random_video() -> Path:
        if not MEDIA_DIR.exists():
            raise VideoGenerationError(
                f"Media folder does not exist: {MEDIA_DIR.as_posix()}"
            )

        candidates = [
            path
            for path in MEDIA_DIR.iterdir()
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        ]

        if not candidates:
            raise VideoGenerationError(
                f"No video files found in media folder: {MEDIA_DIR.as_posix()}"
            )

        return random.choice(candidates)

    @staticmethod
    def _audio_extension() -> str:
        output_format = settings.output_format.lower()
        if output_format.startswith("mp3"):
            return "mp3"
        if output_format.startswith("wav"):
            return "wav"
        if output_format.startswith("opus"):
            return "opus"
        raise VideoGenerationError(
            "Unsupported ElevenLabs output format for ffmpeg pipeline. "
            "Use mp3_*, wav_* or opus_*."
        )

    def _render_video(
        self,
        background_video: Path,
        audio_path: Path,
        subtitles_path: Path,
        output_path: Path,
    ) -> None:
        escaped_subtitles_path = self._escape_subtitles_path(subtitles_path)
        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"subtitles='{escaped_subtitles_path}':"
            f"force_style='{self.SUBTITLE_STYLE}'"
        )

        command = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(background_video),
            "-i",
            str(audio_path),
            "-vf",
            video_filter,
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(output_path),
        ]

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise VideoGenerationError(
                "ffmpeg is not installed or not in PATH"
            ) from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            error_tail = stderr[-1200:] if stderr else "Unknown ffmpeg error"
            raise VideoGenerationError(f"ffmpeg failed: {error_tail}")

    @staticmethod
    def _escape_subtitles_path(path: Path) -> str:
        value = str(path)
        value = value.replace("\\", "\\\\")
        value = value.replace(":", "\\:")
        value = value.replace("'", "\\'")
        value = value.replace(",", "\\,")
        return value
