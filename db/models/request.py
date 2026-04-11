import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.connector import Base


class Request(Base):
    """Database model for video generation requests.

    Tracks user requests for brainrot video generation including
    the input text, estimated duration, and request timestamp.
    Used for quota management and request queueing.

    Attributes:
        id: Auto-incrementing primary key.
        login: User identifier (indexed for fast quota lookups).
        date: UTC timestamp when the request was created.
        text: The input text to convert to speech (up to 10,000 chars).
        duration: Video duration in seconds (estimated initially,
            updated after processing).
    """

    __tablename__ = "requests"
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    login: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    text: Mapped[str] = mapped_column(String(10_000), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
