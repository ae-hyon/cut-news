from fastapi import APIRouter

from app.common.config import settings
from app.presentation.api.routes import articles, auth, categories, health, scraps, summaries, users

health_router = health.router
api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(categories.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(articles.router)
api_router.include_router(scraps.router)
api_router.include_router(summaries.router)
