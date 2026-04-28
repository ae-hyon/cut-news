from fastapi import APIRouter

from app.common.config import settings
from app.presentation.schemas import HealthResponseSchema

router = APIRouter(tags=['health'])


@router.get('/health', response_model=HealthResponseSchema)
def health() -> HealthResponseSchema:
    return HealthResponseSchema(status='ok', app=settings.app_name, version=settings.app_version)
