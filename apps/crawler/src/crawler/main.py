"""Main FastAPI application for the crawler service."""

from fastapi import FastAPI

from crawler.api.router import router as api_router

app = FastAPI(
    title="Crawler Service",
    description="News crawler and scraper service",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"service": "crawler"}
