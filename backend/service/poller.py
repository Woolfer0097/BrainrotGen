"""Background poller for processing video generation requests.

The RequestPoller runs in a background thread, scanning the database
for pending requests and processing them through the video generation pipeline.
Results are written to disk with metadata for the API to retrieve.
"""

import datetime
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from backend.service.video import VideoGenerationService
from db.connector import SessionLocal
from db.models.request import Request
from utils.tts import count_duration

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_ARTIFACTS_DIR = PROJECT_ROOT / "media" / "requests"
"""Directory where request artifacts (videos and metadata) are stored."""


@dataclass(frozen=True)
class PollOnceResult:
    """Result of a single polling iteration.

    Attributes:
        scanned: Number of requests scanned in this batch.
        succeeded: Number of requests successfully processed.
        failed: Number of requests that failed processing.
        last_processed_id: ID of the last request processed.
    """

    scanned: int
    succeeded: int
    failed: int
    last_processed_id: int


class RequestPoller:
    """Background poller for video generation requests.

    Runs continuously in a background thread, fetching pending requests
    from the database and processing them through the video generation pipeline.
    Tracks progress using a persistent state file.

    Attributes:
        poll_interval_seconds: Time to wait between polling when no work.
        batch_size: Maximum requests to fetch per poll.
        artifacts_dir: Directory for storing generated videos.
        state_path: JSON file for persisting last processed ID.
        session_factory: SQLAlchemy session factory.
        video_service: Service for generating videos.
    """

    def __init__(
        self,
        *,
        poll_interval_seconds: float = 2.0,
        batch_size: int = 10,
        artifacts_dir: Path | None = None,
        state_path: Path | None = None,
        session_factory: sessionmaker[Session] = SessionLocal,
        video_service: VideoGenerationService | None = None,
    ) -> None:
        self.poll_interval_seconds = max(0.1, poll_interval_seconds)
        self.batch_size = max(1, batch_size)
        self.artifacts_dir = artifacts_dir or REQUEST_ARTIFACTS_DIR
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = state_path or (
            self.artifacts_dir / ".poller_state.json"
        )
        self.session_factory = session_factory
        self.video_service = video_service or VideoGenerationService()

        self._last_processed_id = self._load_last_processed_id()
        self._stop_event = Event()
        self._thread: Thread | None = None

    @property
    def last_processed_id(self) -> int:
        return self._last_processed_id

    def start_in_background(self, name: str = "request-poller") -> None:
        """Start the poller in a daemon thread.

        Args:
            name: Thread name for debugging.
        """
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = Thread(target=self.run_forever, name=name, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the poller to stop at next iteration."""
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        """Wait for the poller thread to finish.

        Args:
            timeout: Maximum seconds to wait. None waits indefinitely.
        """
        if self._thread:
            self._thread.join(timeout)

    def run_forever(self) -> None:
        logger.info(
            "Request poller started: "
            "batch_size=%s, poll_interval_seconds=%s, last_id=%s",
            self.batch_size,
            self.poll_interval_seconds,
            self._last_processed_id,
        )
        while not self._stop_event.is_set():
            result = self.poll_once()
            if result.scanned == 0:
                self._stop_event.wait(self.poll_interval_seconds)

    def poll_once(self) -> PollOnceResult:
        """Execute a single polling iteration.

        Fetches the next batch of pending requests and processes them.

        Returns:
            Statistics about this polling iteration.
        """
        with self.session_factory() as db:
            requests = self._fetch_next_batch(db)

        succeeded = 0
        failed = 0

        for request in requests:
            request_id = self._to_int_id(request.id)
            ok = self._process_request(request)
            if ok:
                succeeded += 1
            else:
                failed += 1

            self._last_processed_id = request_id
            self._save_last_processed_id(request_id)

        return PollOnceResult(
            scanned=len(requests),
            succeeded=succeeded,
            failed=failed,
            last_processed_id=self._last_processed_id,
        )

    def _fetch_next_batch(self, db: Session) -> list[Request]:
        """Fetch the next batch of unprocessed requests from the database.

        Args:
            db: Active SQLAlchemy session.

        Returns:
            List of Request objects to process, ordered by ID.
        """
        max_request_id = db.execute(select(func.max(Request.id))).scalar()
        max_request_id_int = (
            self._to_int_id(max_request_id)
            if max_request_id is not None
            else 0
        )
        if max_request_id_int < self._last_processed_id:
            logger.warning(
                "Poller cursor reset: last_processed_id=%s, max_request_id=%s",
                self._last_processed_id,
                max_request_id_int,
            )
            self._last_processed_id = 0
            self._save_last_processed_id(0)

        stmt = (
            select(Request)
            .where(Request.id > self._last_processed_id)
            .order_by(Request.id.asc())
            .limit(self.batch_size)
        )
        return list(db.execute(stmt).scalars().all())

    def _process_request(self, request: Request) -> bool:
        """Process a single video generation request.

        Generates the video, writes it to disk, and updates the database
        with the actual duration. Writes metadata file with status.

        Args:
            request: The Request object to process.

        Returns:
            True if processing succeeded, False otherwise.
        """
        request_id = self._to_int_id(request.id)
        request_dir = self.artifacts_dir / str(request_id)
        request_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "request_id": request_id,
            "login": request.login,
            "request_date": request.date.isoformat(),
            "text": request.text,
            "duration": request.duration,
            "processed_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }
        try:
            video_bytes, audio_bytes = self.video_service.generate_with_audio(
                request.text,
            )
            (request_dir / "video.mp4").write_bytes(video_bytes)
            actual_duration = count_duration(audio_bytes)
            with self.session_factory() as db:
                stmt = (
                    update(Request)
                    .where(Request.id == request_id)
                    .values(duration=actual_duration)
                )
                db.execute(stmt)
                db.commit()
            meta["ok"] = True
            meta["actual_duration"] = actual_duration
            self._write_json(request_dir / "meta.json", meta)
            return True
        except Exception as exc:
            meta["ok"] = False
            meta["error"] = str(exc)
            self._write_json(request_dir / "meta.json", meta)
            logger.exception("Failed to process request id=%s", request_id)
            return False

    def _load_last_processed_id(self) -> int:
        """Load the last processed request ID from state file.

        Returns:
            The last processed ID, or 0 if no state exists.
        """
        if not self.state_path.exists():
            return 0

        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            return max(0, int(payload.get("last_processed_id", 0)))
        except (ValueError, TypeError, json.JSONDecodeError):
            logger.warning(
                "Invalid poller state file %s, cursor reset to 0",
                self.state_path.as_posix(),
            )
            return 0

    def _save_last_processed_id(self, request_id: int) -> None:
        """Persist the last processed request ID to state file.

        Args:
            request_id: The ID to save as last processed.
        """
        payload = {
            "last_processed_id": request_id,
            "updated_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }
        self._write_json(self.state_path, payload)

    @staticmethod
    def _to_int_id(value: object) -> int:
        """Convert a value to integer ID safely.

        Args:
            value: Any value that can be converted to int.

        Returns:
            Integer representation of the value.
        """
        if isinstance(value, int):
            return value
        return int(str(value))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        """Write JSON data atomically using a temp file.

        Args:
            path: Target path for the JSON file.
            payload: Dictionary to serialize as JSON.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(path)
