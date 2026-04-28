from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_feed_service
from app.presentation.schemas import ScrapToggleResponseSchema

router = APIRouter(tags=['scraps'])


@router.put('/users/{user_id}/scraps/{article_id}', response_model=ScrapToggleResponseSchema)
def add_scrap(user_id: str, article_id: str, service: FeedService = Depends(get_feed_service)):
    try:
        service.add_scrap(user_id, article_id)
        return ScrapToggleResponseSchema(user_id=user_id, article_id=article_id, scrapped=True)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete('/users/{user_id}/scraps/{article_id}', response_model=ScrapToggleResponseSchema)
def remove_scrap(user_id: str, article_id: str, service: FeedService = Depends(get_feed_service)):
    service.remove_scrap(user_id, article_id)
    return ScrapToggleResponseSchema(user_id=user_id, article_id=article_id, scrapped=False)
