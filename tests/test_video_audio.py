import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
import backend.service.video as video_module
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


def test_random_start_offset_seconds_uses_non_zero_bounds(
    monkeypatch,
) -> None:
    recorded: dict[str, float] = {}

    def fake_uniform(start: float, end: float) -> float:
        recorded["start"] = start
        recorded["end"] = end
        return 3.7

    monkeypatch.setattr(video_module.random, "uniform", fake_uniform)
    offset = VideoGenerationService._random_start_offset_seconds(12.0)
    assert offset == 3.7
    assert recorded["start"] == pytest.approx(0.25)
    assert recorded["end"] == pytest.approx(11.75)


def test_random_start_offset_seconds_returns_zero_when_unknown() -> None:
    assert VideoGenerationService._random_start_offset_seconds(None) == 0.0


def test_probe_video_duration_seconds_parses_ffprobe(monkeypatch) -> None:
    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command[0] == "ffprobe"
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(command, 0, stdout="8.4\n", stderr="")

    monkeypatch.setattr(video_module.subprocess, "run", fake_run)
    duration = VideoGenerationService._probe_video_duration_seconds(
        Path("/tmp/video.mp4")
    )
    assert duration == pytest.approx(8.4)


def test_probe_video_duration_seconds_returns_none_on_error(
    monkeypatch,
) -> None:
    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="bad input"
        )

    monkeypatch.setattr(video_module.subprocess, "run", fake_run)
    duration = VideoGenerationService._probe_video_duration_seconds(
        Path("/tmp/video.mp4")
    )
    assert duration is None


def test_background_music_path_resolves_existing_file(
    monkeypatch, tmp_path
) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()
    music = media_dir / "musica.m4a"
    music.write_bytes(b"fake")

    monkeypatch.setattr(video_module, "MEDIA_DIR", media_dir)
    resolved = VideoGenerationService._background_music_path()
    assert resolved == music


def test_background_music_path_raises_when_missing(
    monkeypatch, tmp_path
) -> None:
    media_dir = tmp_path / "media"
    media_dir.mkdir()

    monkeypatch.setattr(video_module, "MEDIA_DIR", media_dir)
    with pytest.raises(VideoGenerationError, match="Background music file"):
        VideoGenerationService._background_music_path()


def test_render_video_includes_seek_offset(monkeypatch, tmp_path) -> None:
    service = VideoGenerationService()
    background_video = tmp_path / "bg.mp4"
    background_music_path = tmp_path / "musica.m4a"
    audio_path = tmp_path / "voice.mp3"
    subtitles_path = tmp_path / "subtitles.srt"
    output_path = tmp_path / "out.mp4"

    captured: dict[str, list[str]] = {}

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(video_module.subprocess, "run", fake_run)

    service._render_video(
        background_video=background_video,
        background_start_offset=5.4321,
        background_music_path=background_music_path,
        audio_path=audio_path,
        audio_input_args=(),
        subtitles_path=subtitles_path,
        output_path=output_path,
    )

    command = captured["command"]
    assert "-ss" in command
    first_offset_idx = command.index("-ss")
    assert command[first_offset_idx + 1] == "5.432"

    second_offset_idx = command.index("-ss", first_offset_idx + 1)
    assert command[second_offset_idx + 1] == "37.000"

    filter_complex_idx = command.index("-filter_complex")
    assert "volume=0.120" in command[filter_complex_idx + 1]
    assert "[voice][music]amix" in command[filter_complex_idx + 1]

    map_idx = command.index("-map")
    assert command[map_idx + 1] == "0:v:0"
    assert command[map_idx + 3] == "[aout]"
