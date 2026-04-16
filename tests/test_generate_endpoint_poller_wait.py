import json
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.api.v1.endpoints import generate  # noqa: E402


def test_wait_for_processed_video_returns_bytes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "REQUEST_ARTIFACTS_DIR", tmp_path)
    request_dir = tmp_path / "1"
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "meta.json").write_text(
        json.dumps(
            {
                "request_id": 1,
                "request_date": "2026-01-01T00:00:00",
                "ok": True,
            }
        ),
        encoding="utf-8",
    )
    (request_dir / "video.mp4").write_bytes(b"video-data")

    result = generate._wait_for_processed_video(
        request_id=1,
        expected_request_date="2026-01-01T00:00:00",
        timeout_seconds=0.2,
        interval_seconds=0.01,
    )

    assert result == b"video-data"


def test_wait_for_processed_video_raises_on_meta_error(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(generate, "REQUEST_ARTIFACTS_DIR", tmp_path)
    request_dir = tmp_path / "2"
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "meta.json").write_text(
        json.dumps(
            {
                "request_id": 2,
                "request_date": "2026-01-01T00:00:00",
                "ok": False,
                "error": "boom",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(HTTPException) as exc:
        generate._wait_for_processed_video(
            request_id=2,
            expected_request_date="2026-01-01T00:00:00",
            timeout_seconds=0.2,
            interval_seconds=0.01,
        )

    assert exc.value.status_code == 500
    assert exc.value.detail == "boom"


def test_wait_for_processed_video_times_out(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generate, "REQUEST_ARTIFACTS_DIR", tmp_path)

    with pytest.raises(HTTPException) as exc:
        generate._wait_for_processed_video(
            request_id=3,
            expected_request_date="2026-01-01T00:00:00",
            timeout_seconds=0.1,
            interval_seconds=0.01,
        )

    assert exc.value.status_code == 504


def test_wait_for_processed_video_ignores_stale_request_meta(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(generate, "REQUEST_ARTIFACTS_DIR", tmp_path)
    request_dir = tmp_path / "4"
    request_dir.mkdir(parents=True, exist_ok=True)
    (request_dir / "meta.json").write_text(
        json.dumps(
            {
                "request_id": 4,
                "request_date": "2025-01-01T00:00:00",
                "ok": True,
            }
        ),
        encoding="utf-8",
    )
    (request_dir / "video.mp4").write_bytes(b"stale-video")

    with pytest.raises(HTTPException) as exc:
        generate._wait_for_processed_video(
            request_id=4,
            expected_request_date="2026-01-01T00:00:00",
            timeout_seconds=0.1,
            interval_seconds=0.01,
        )

    assert exc.value.status_code == 504
