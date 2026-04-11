"""User quota management for video generation.

Tracks daily usage per user and enforces a 5-minute (300 second) quota.
Quota resets at midnight UTC each day.
"""

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from db.connector import Base, SessionLocal, engine
from db.models.request import Request
from utils.tts import estimate_duration

DAILY_QUOTA_SECONDS = 300
"""Daily quota limit in seconds (5 minutes per user)."""

Base.metadata.create_all(bind=engine)


def get_today_duration_sum(
    login: str,
    date: datetime.date,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> int:
    """Calculate total video duration for a user on a specific date.

    Args:
        login: User identifier to query.
        date: The date to calculate usage for.
        session_factory: SQLAlchemy session factory.

    Returns:
        Total seconds of video generated for the user on that date.
    """
    with session_factory() as db:
        start = datetime.datetime.combine(date, datetime.time.min)
        end = datetime.datetime.combine(date, datetime.time.max)
        stmt = (
            select(func.coalesce(func.sum(Request.duration), 0))
            .where(Request.login == login)
            .where(Request.date >= start)
            .where(Request.date <= end)
        )
        result = db.execute(stmt).scalar()
        return int(result) if result is not None else 0


def can_accept_request(
    login: str,
    text: str,
    date: datetime.date | None = None,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> bool:
    """Check if a new request would exceed the user's daily quota.

    Args:
        login: User identifier to check quota for.
        text: The text to estimate duration from.
        date: Date to check (defaults to today).
        session_factory: SQLAlchemy session factory.

    Returns:
        True if the request can be accepted without exceeding quota.
    """
    if date is None:
        date = datetime.datetime.now(datetime.timezone.utc).date()
    estimated = estimate_duration(text)
    current = get_today_duration_sum(login, date, session_factory)
    return current + estimated <= DAILY_QUOTA_SECONDS
