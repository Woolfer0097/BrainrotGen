import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.service.video import VideoGenerationError, VideoGenerationService


def test_audio_input_spec_supports_alaw(monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_format", "alaw_8000")
    spec = VideoGenerationService._audio_input_spec()
    assert spec.extension == "alaw"
    assert spec.ffmpeg_input_args == (
        "-f",
        "alaw",
        "-ar",
        "8000",
        "-ac",
        "1",
    )


def test_audio_input_spec_supports_pcm(monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_format", "pcm_44100")
    spec = VideoGenerationService._audio_input_spec()
    assert spec.extension == "pcm"
    assert spec.ffmpeg_input_args == (
        "-f",
        "s16le",
        "-ar",
        "44100",
        "-ac",
        "1",
    )


def test_audio_input_spec_rejects_unknown_format(monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_format", "flac_44100")
    with pytest.raises(VideoGenerationError):
        VideoGenerationService._audio_input_spec()


def test_audio_input_spec_rejects_invalid_sample_rate(monkeypatch) -> None:
    monkeypatch.setattr(settings, "output_format", "alaw_fast")
    with pytest.raises(VideoGenerationError):
        VideoGenerationService._audio_input_spec()
