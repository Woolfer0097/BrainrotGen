import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from db.connector import Base


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, index=True)
    login: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    text: Mapped[str] = mapped_column(String(10_000), nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
