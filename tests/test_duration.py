import subprocess
import sys
from io import BytesIO
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils   import tts


def test_estimate_duration_includes_punctuation_pauses() -> None:
    result = tts.estimate_duration("Hello, world!")
    assert result == pytest.approx(1.2)


def test_count_duration_returns_zero_for_empty_audio() -> None:
    result = tts.count_duration(b"")
    assert result == 0


def test_count_duration_uses_ffprobe_value(monkeypatch) -> None:
    def fake_run(
        command: list[str],
        *,
        input: bytes,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[bytes]:
        assert command[0] == "ffprobe"
        assert input == b"audio-bytes"
        assert capture_output is True
        assert check is False
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=b"2.4\n",
            stderr=b"",
        )

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    result = tts.count_duration(BytesIO(b"audio-bytes"))
    assert result == 2


def test_count_duration_falls_back_when_ffprobe_fails(
    monkeypatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        input: bytes,
        capture_output: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=b"",
            stderr=b"invalid stream",
        )

    monkeypatch.setattr(tts.subprocess, "run", fake_run)
    result = tts.count_duration(b"A" * 64_000)
    assert result == 4
