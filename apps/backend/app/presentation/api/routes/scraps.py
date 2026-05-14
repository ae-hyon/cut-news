from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.domain.entities import AuthSession
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_feed_service, require_current_user
from app.presentation.schemas import ScrapListResponseSchema, ScrapToggleResponseSchema

router = APIRouter(tags=['me'])

SCRAP_RESPONSES = {401: {'description': 'Authentication required'}, 404: {'description': 'Article not found'}}


@router.get(
    '/me/scraps',
    response_model=ScrapListResponseSchema,
    summary='List my saved articles',
    description='Returns the authenticated user scraps. Items are article cards and always have is_scrapped=true.',
    responses={401: {'description': 'Authentication required'}},
)
def get_my_scraps(
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return ScrapListResponseSchema.from_entities(session.user_id, service.list_scraps(session.user_id), service)


@router.put(
    '/me/scraps/{article_id}',
    response_model=ScrapToggleResponseSchema,
    summary='Save an article',
    description='Adds the article to the authenticated user scraps and returns scrapped=true.',
    responses=SCRAP_RESPONSES,
)
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


@router.delete(
    '/me/scraps/{article_id}',
    response_model=ScrapToggleResponseSchema,
    summary='Unsave an article',
    description='Removes the article from the authenticated user scraps and returns scrapped=false. Idempotent if already absent.',
    responses={401: {'description': 'Authentication required'}},
)
def remove_my_scrap(
    article_id: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    service.remove_scrap(session.user_id, article_id)
    return ScrapToggleResponseSchema(user_id=session.user_id, article_id=article_id, scrapped=False)
