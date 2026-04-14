"""API router for crawler endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    """Root API endpoint."""
    return {"message": "Crawler API"}
