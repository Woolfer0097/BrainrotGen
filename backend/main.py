from fastapi import FastAPI

from backend.api.v1.router import router as api_v1_router
from backend.config import settings
from backend.service.poller_runtime import (start_request_poller,
                                            stop_request_poller)
from db.connector import Base, engine
from db.models import Request  # noqa: F401

app = FastAPI(
    title=settings.app_name, version=settings.app_version, debug=settings.debug
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    start_request_poller()


@app.on_event("shutdown")
def on_shutdown() -> None:
    stop_request_poller()


app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
