from fastapi import FastAPI

from app.api.v1.router import router as api_v1_router
from app.config import settings
from db.connector import Base, engine
from db.models import Item  # noqa: F401

app = FastAPI(
    title=settings.app_name, version=settings.app_version, debug=settings.debug
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
