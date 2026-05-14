from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.common.config import settings
from app.infrastructure.database import init_database
from app.presentation.api.router import api_router, health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        'Frontend integration contract for the real Next frontend at http://127.0.0.1:3000.\n\n'
        'Browser requests from frontend must use credentials: include so the HttpOnly auth cookies are sent. '
        'The legacy apps/test-frontend Vite app is deprecated and is not the source of truth for API integration.\n\n'
        'Use /v1/me to decide frontend routing from session_state: anonymous, authenticated, or onboarded.'
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_app_url],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(health_router)
app.include_router(api_router)
