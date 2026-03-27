from fastapi import APIRouter

from app.api.v1.endpoints import health, items

router = APIRouter()
router.include_router(health.router)
router.include_router(items.router)
