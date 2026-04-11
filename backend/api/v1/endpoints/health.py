from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Returns the current health status of the API. "
    "Use this endpoint to verify the service is running and responsive.",
    response_description="A simple status object indicating the API is healthy",
)
def healthcheck() -> dict[str, str]:
    """Return API health status.

    Returns:
        A dictionary with a single key "status" set to "ok".
    """
    return {"status": "ok"}
