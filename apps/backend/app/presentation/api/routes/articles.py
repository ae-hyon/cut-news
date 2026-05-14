from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.domain.entities import AuthSession
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_feed_service, require_current_user
from app.presentation.schemas import ArticleDetailResponseSchema

router = APIRouter(tags=['articles'])


PROTECTED_RESPONSES = {401: {'description': 'Authentication required'}, 404: {'description': 'Article not found'}}


@router.get(
    '/articles/{article_id}',
    response_model=ArticleDetailResponseSchema,
    summary='Get article detail for current user',
    description=(
        'Returns article detail using the current authenticated user so is_scrapped reflects that user. '
        'Prefer /v1/me/articles/{article_id} for new frontend code; this route is kept as an equivalent detail alias.'
    ),
    responses=PROTECTED_RESPONSES,
)
def get_article(
    article_id: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    try:
        return ArticleDetailResponseSchema.from_entity(service.get_article(article_id), service, session.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    '/me/articles/{article_id}',
    response_model=ArticleDetailResponseSchema,
    tags=['me'],
    summary='Get my article detail',
    description='Recommended frontend detail endpoint. Requires auth and returns content plus user-specific is_scrapped.',
    responses=PROTECTED_RESPONSES,
)
def get_my_article(
    article_id: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    try:
        return ArticleDetailResponseSchema.from_entity(service.get_article(article_id), service, session.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
