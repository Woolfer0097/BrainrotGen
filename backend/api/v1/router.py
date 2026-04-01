from fastapi import APIRouter

from backend.api.v1.endpoints import generate, health

router = APIRouter()
router.include_router(health.router)
router.include_router(generate.router)
