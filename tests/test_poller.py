import datetime
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.service import poller as poller_module
from backend.service.poller import RequestPoller
from db.connector import Base
from db.models.request import Request


@pytest.fixture
def session_factory(tmp_path: Path) -> sessionmaker:
    db_path = tmp_path / "poller-test.db"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    try:
        yield factory
    finally:
        engine.dispose()


def insert_request(
    session_factory: sessionmaker,
    *,
    login: str = "alice",
    text: str = "hello world",
    duration: int = 2,
    date: datetime.datetime | None = None,
) -> Request:
    request = Request(
        login=login,
        text=text,
        duration=duration,
        date=date or datetime.datetime(2025, 1, 1, 12, 0, 0),
    )
    with session_factory() as db:
        db.add(request)
        db.commit()
        db.refresh(request)
        db.expunge(request)
    return request


class SuccessfulVideoService:
    def __init__(
        self, video_bytes: bytes = b"video", audio_bytes: bytes = b"audio"
    ):
        self.video_bytes = video_bytes
        self.audio_bytes = audio_bytes
        self.calls: list[str] = []

    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        self.calls.append(text)
        return self.video_bytes, self.audio_bytes


class ConditionalVideoService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        self.calls.append(text)
        if "fail" in text:
            raise RuntimeError("boom")
        return b"video:" + text.encode("utf-8"), b"audio"


class FailingVideoService:
    def generate_with_audio(self, text: str) -> tuple[bytes, bytes]:
        raise RuntimeError(f"failed for {text}")


def test_constructor_clamps_intervals_and_creates_artifacts_dir(
    tmp_path: Path,
    session_factory: sessionmaker,
) -> None:
    artifacts_dir = tmp_path / "artifacts"

    poller = RequestPoller(
        poll_interval_seconds=0,
        batch_size=0,
        artifacts_dir=artifacts_dir,
        session_factory=session_factory,
        video_service=SuccessfulVideoService(),
    )

    assert poller.poll_interval_seconds == 0.1
    assert poller.batch_size == 1
    assert artifacts_dir.exists()


def test_load_last_processed_id_returns_zero_when_state_file_is_invalid(
    tmp_path: Path,
    session_factory: sessionmaker,
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text("{not-json", encoding="utf-8")

    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        state_path=state_path,
        session_factory=session_factory,
        video_service=SuccessfulVideoService(),
    )

    assert poller.last_processed_id == 0


def test_save_last_processed_id_writes_state_file(
    tmp_path: Path,
    session_factory: sessionmaker,
) -> None:
    state_path = tmp_path / "state.json"
    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        state_path=state_path,
        session_factory=session_factory,
        video_service=SuccessfulVideoService(),
    )

    poller._save_last_processed_id(7)

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["last_processed_id"] == 7
    assert "updated_at" in payload
    assert not state_path.with_name("state.json.tmp").exists()


def test_fetch_next_batch_returns_rows_after_cursor_in_id_order(
    tmp_path: Path,
    session_factory: sessionmaker,
) -> None:
    first = insert_request(session_factory, text="first")
    second = insert_request(session_factory, text="second")
    third = insert_request(session_factory, text="third")

    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        session_factory=session_factory,
        video_service=SuccessfulVideoService(),
        batch_size=2,
    )
    poller._last_processed_id = first.id

    with session_factory() as db:
        batch = poller._fetch_next_batch(db)

    assert [request.id for request in batch] == [second.id, third.id]


def test_poll_once_resets_cursor_when_database_ids_restart(
    tmp_path: Path,
    session_factory: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = insert_request(session_factory, text="fresh")
    monkeypatch.setattr(poller_module, "count_duration", lambda audio: 3)
    state_path = tmp_path / "state.json"
    state_path.write_text(
        json.dumps({"last_processed_id": 50}),
        encoding="utf-8",
    )
    service = SuccessfulVideoService(
        video_bytes=b"new-video",
        audio_bytes=b"new-audio",
    )
    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        state_path=state_path,
        session_factory=session_factory,
        video_service=service,
    )

    assert poller.last_processed_id == 50

    result = poller.poll_once()

    assert result.scanned == 1
    assert result.succeeded == 1
    assert result.failed == 0
    assert result.last_processed_id == request.id
    assert service.calls == ["fresh"]

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["last_processed_id"] == request.id


def test_process_request_writes_artifacts_and_updates_duration(
    tmp_path: Path,
    session_factory: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = insert_request(
        session_factory,
        login="alice",
        text="ship this",
        duration=2,
    )
    service = SuccessfulVideoService(
        video_bytes=b"mp4-bytes", audio_bytes=b"raw-audio"
    )
    monkeypatch.setattr(poller_module, "count_duration", lambda audio: 9)
    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        session_factory=session_factory,
        video_service=service,
    )

    ok = poller._process_request(request)

    assert ok is True
    request_dir = tmp_path / "artifacts" / str(request.id)
    assert (request_dir / "video.mp4").read_bytes() == b"mp4-bytes"

    meta = json.loads((request_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["request_id"] == request.id
    assert meta["login"] == "alice"
    assert meta["text"] == "ship this"
    assert meta["duration"] == 2
    assert meta["ok"] is True
    assert meta["actual_duration"] == 9

    with session_factory() as db:
        stored = db.get(Request, request.id)

    assert stored is not None
    assert stored.duration == 9
    assert service.calls == ["ship this"]


def test_process_request_failure_writes_error_metadata_and_keeps_duration(
    tmp_path: Path,
    session_factory: sessionmaker,
) -> None:
    request = insert_request(
        session_factory,
        login="alice",
        text="bad input",
        duration=4,
    )
    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        session_factory=session_factory,
        video_service=FailingVideoService(),
    )

    ok = poller._process_request(request)

    assert ok is False
    request_dir = tmp_path / "artifacts" / str(request.id)
    meta = json.loads((request_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["ok"] is False
    assert meta["error"] == "failed for bad input"
    assert not (request_dir / "video.mp4").exists()

    with session_factory() as db:
        stored = db.get(Request, request.id)

    assert stored is not None
    assert stored.duration == 4


def test_poll_once_aggregates_results_updates_state_and_advances_cursor(
    tmp_path: Path,
    session_factory: sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = insert_request(
        session_factory, login="alice", text="ok request", duration=1
    )
    second = insert_request(
        session_factory, login="alice", text="please fail", duration=2
    )
    monkeypatch.setattr(poller_module, "count_duration", lambda audio: 6)
    state_path = tmp_path / "state.json"
    service = ConditionalVideoService()
    poller = RequestPoller(
        artifacts_dir=tmp_path / "artifacts",
        state_path=state_path,
        session_factory=session_factory,
        video_service=service,
        batch_size=10,
    )

    result = poller.poll_once()

    assert result.scanned == 2
    assert result.succeeded == 1
    assert result.failed == 1
    assert result.last_processed_id == second.id
    assert poller.last_processed_id == second.id
    assert (
        json.loads(state_path.read_text(encoding="utf-8"))["last_processed_id"]
        == second.id
    )
    assert service.calls == ["ok request", "please fail"]

    first_dir = tmp_path / "artifacts" / str(first.id)
    second_dir = tmp_path / "artifacts" / str(second.id)
    assert (first_dir / "video.mp4").read_bytes() == b"video:ok request"

    first_meta = json.loads(
        (first_dir / "meta.json").read_text(encoding="utf-8")
    )
    second_meta = json.loads(
        (second_dir / "meta.json").read_text(encoding="utf-8")
    )
    assert first_meta["ok"] is True
    assert first_meta["actual_duration"] == 6
    assert second_meta["ok"] is False
    assert second_meta["error"] == "boom"

    with session_factory() as db:
        first_row = db.get(Request, first.id)
        second_row = db.get(Request, second.id)

    assert first_row is not None
    assert second_row is not None
    assert first_row.duration == 6
    assert second_row.duration == 2
