from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_feed_service
from app.presentation.schemas import ArticleDetailResponseSchema

router = APIRouter(tags=['articles'])


@router.get('/articles/{article_id}', response_model=ArticleDetailResponseSchema)
def get_article(article_id: str, user_id: str | None = None, service: FeedService = Depends(get_feed_service)):
    try:
        return ArticleDetailResponseSchema.from_entity(service.get_article(article_id), service, user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
