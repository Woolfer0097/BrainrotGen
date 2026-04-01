import datetime

from pydantic import BaseModel


class RequestCreate(BaseModel):
    login: str
    text: str
    duration: int


class RequestRead(BaseModel):
    id: int
    login: str
    date: datetime.datetime
    text: str
    duration: int
