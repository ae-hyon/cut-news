from fastapi import APIRouter, Depends, HTTPException

from app.application.services.catalog_service import CatalogService
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_catalog_service
from app.presentation.schemas import CategoryResponseSchema

router = APIRouter(tags=['categories'])


@router.get('/categories', response_model=list[CategoryResponseSchema])
def list_categories(service: CatalogService = Depends(get_catalog_service)):
    return [CategoryResponseSchema.from_entity(item) for item in service.list_categories()]


@router.get('/categories/{slug}', response_model=CategoryResponseSchema)
def get_category(slug: str, service: CatalogService = Depends(get_catalog_service)):
    try:
        return CategoryResponseSchema.from_entity(service.get_category(slug))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
