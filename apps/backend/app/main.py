from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.common.config import settings
from app.infrastructure.database import init_database
from app.presentation.api.router import api_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.include_router(health_router)
app.include_router(api_router)
