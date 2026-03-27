from gtts import gTTS
from io import BytesIO

import re
from pydub import AudioSegment


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


def count_duration(buffer: BytesIO) -> int:
    audio = AudioSegment.from_file(buffer, format="mp3")
    duration_sec = len(audio) / 1000
    return duration_sec
