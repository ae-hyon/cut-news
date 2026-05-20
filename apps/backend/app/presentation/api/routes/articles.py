from fastapi import APIRouter, Depends, HTTPException

from app.application.services.daily_feed_snapshot_service import DailyFeedSnapshotService
from app.application.services.feed_service import FeedService
from app.domain.entities import AuthSession
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_daily_feed_snapshot_service, get_feed_service, require_current_user
from app.presentation.schemas import ArticleDetailResponseSchema

router = APIRouter(tags=['articles'])


PROTECTED_RESPONSES = {401: {'description': 'Authentication required'}, 404: {'description': 'Article not found'}}


def _get_article_detail(
    article_id: str,
    snapshot_id: int | None,
    session: AuthSession,
    service: FeedService,
    snapshot_service: DailyFeedSnapshotService,
) -> ArticleDetailResponseSchema:
    try:
        article = service.get_article(article_id)
        assert session.user_id is not None
        snapshot_service.mark_article_read(session.user_id, article_id, snapshot_id, read_source='article_detail')
        return ArticleDetailResponseSchema.from_entity(article, service, session.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    '/articles/{article_id}',
    response_model=ArticleDetailResponseSchema,
    summary='Get article detail for current user',
    description=(
        'Returns article detail using the current authenticated user so is_scrapped reflects that user. '
        'Opening detail marks the article read; pass optional snapshot_id query to update snapshot read/completion state. '
        'Prefer /v1/me/articles/{article_id} for new frontend code; this route is kept as an equivalent detail alias.'
    ),
    responses=PROTECTED_RESPONSES,
)
def get_article(
    article_id: str,
    snapshot_id: int | None = None,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
    snapshot_service: DailyFeedSnapshotService = Depends(get_daily_feed_snapshot_service),
):
    return _get_article_detail(article_id, snapshot_id, session, service, snapshot_service)


@router.get(
    '/me/articles/{article_id}',
    response_model=ArticleDetailResponseSchema,
    tags=['me'],
    summary='Get my article detail',
    description=(
        'Recommended frontend detail endpoint. Requires auth and returns content plus user-specific is_scrapped. '
        'Opening detail marks the article read; pass optional snapshot_id query from feed/archive context to update snapshot read/completion state.'
    ),
    responses=PROTECTED_RESPONSES,
)
def get_my_article(
    article_id: str,
    snapshot_id: int | None = None,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
    snapshot_service: DailyFeedSnapshotService = Depends(get_daily_feed_snapshot_service),
):
    return _get_article_detail(article_id, snapshot_id, session, service, snapshot_service)
