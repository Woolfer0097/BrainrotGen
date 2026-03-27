import datetime
from uuid import UUID

from pydantic import BaseModel


class RequestCreate(BaseModel):
    login: str
    text: str
    duration: int


class RequestRead(BaseModel):
    id: UUID
    login: str
    date: datetime.datetime
    text: str
    duration: int
