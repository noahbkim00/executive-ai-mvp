"""Health check router."""

from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/ready")
async def ready_check():
    """Readiness check endpoint."""
    return {"status": "ok", "ready": True}