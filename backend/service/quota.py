import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.service.video import estimate_duration
from db.connector import Base, SessionLocal, engine
from db.models.request import Request

DAILY_QUOTA_SECONDS = 300

Base.metadata.create_all(bind=engine)


def get_today_duration_sum(
    login: str,
    date: datetime.date,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> int:
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
    if date is None:
        date = datetime.datetime.now(datetime.timezone.utc).date()
    estimated = estimate_duration(text)
    current = get_today_duration_sum(login, date, session_factory)
    return current + estimated <= DAILY_QUOTA_SECONDS
