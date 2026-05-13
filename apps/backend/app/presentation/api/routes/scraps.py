from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.domain.entities import AuthSession
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_feed_service, require_current_user
from app.presentation.schemas import ScrapListResponseSchema, ScrapToggleResponseSchema

router = APIRouter(tags=['me'])


@router.get('/me/scraps', response_model=ScrapListResponseSchema)
def get_my_scraps(
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return ScrapListResponseSchema.from_entities(session.user_id, service.list_scraps(session.user_id), service)


@router.put('/me/scraps/{article_id}', response_model=ScrapToggleResponseSchema)
def add_my_scrap(
    article_id: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    try:
        service.add_scrap(session.user_id, article_id)
        return ScrapToggleResponseSchema(user_id=session.user_id, article_id=article_id, scrapped=True)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete('/me/scraps/{article_id}', response_model=ScrapToggleResponseSchema)
def remove_my_scrap(
    article_id: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    service.remove_scrap(session.user_id, article_id)
    return ScrapToggleResponseSchema(user_id=session.user_id, article_id=article_id, scrapped=False)
