import re
import subprocess
from io import BytesIO

from gtts import gTTS


def generate_audio_bytes(text: str) -> BytesIO:
    """
    Generate TTS in English from the given text.
    Returns BytesIO so we can send it directly without saving to disk.
    """
    audio_fp = BytesIO()
    tts = gTTS(text, lang="en")
    tts.write_to_fp(audio_fp)
    audio_fp.seek(0)  # Move cursor back to the start
    return audio_fp


def estimate_duration(text: str, wpm: int = 150) -> float:
    words = len(text.split())
    base = words / wpm * 60

    # punctuation penalty (~small pauses)
    pauses = len(re.findall(r"[.,!?;:]", text))
    return base + pauses * 0.2


def count_duration(buffer: bytes | bytearray | memoryview | BytesIO) -> int:
    audio_bytes = _to_audio_bytes(buffer)
    if not audio_bytes:
        return 0

    probed_duration = _probe_duration_seconds(audio_bytes)
    if probed_duration is not None:
        return max(1, int(round(probed_duration)))

    return _fallback_duration_seconds(audio_bytes)


def _to_audio_bytes(
    buffer: bytes | bytearray | memoryview | BytesIO,
) -> bytes:
    if isinstance(buffer, BytesIO):
        return buffer.getvalue()
    return bytes(buffer)


def _probe_duration_seconds(audio_bytes: bytes) -> float | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        "-i",
        "pipe:0",
    ]
    try:
        completed = subprocess.run(
            command,
            input=audio_bytes,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None

    if completed.returncode != 0:
        return None

    output = completed.stdout.decode("utf-8", errors="ignore").strip()
    try:
        duration = float(output)
    except ValueError:
        return None

    if duration <= 0:
        return None
    return duration


def _fallback_duration_seconds(audio_bytes: bytes) -> int:
    estimated_seconds = len(audio_bytes) * 8 / 128_000
    return max(1, int(round(estimated_seconds)))
