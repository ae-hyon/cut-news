from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException

from app.application.services.daily_feed_snapshot_service import DailyFeedSnapshotService
from app.application.services.feed_service import FeedService
from app.application.services.user_service import UserPreferenceService
from app.domain.entities import AuthSession
from app.domain.exceptions import NotFoundError, ValidationError
from app.presentation.api.dependencies import get_daily_feed_snapshot_service, get_feed_service, get_user_preference_service, require_current_user
from app.presentation.schemas import (
    ArchiveDateResponseSchema,
    ArchiveMonthResponseSchema,
    FeedResponseSchema,
    UserPreferenceResponseSchema,
    UserPreferenceUpdateRequestSchema,
)

router = APIRouter(tags=['me'])

AUTH_REQUIRED = {401: {'description': 'Authentication required'}}


@dataclass(frozen=True)
class HomeFeedWindow:
    publication_status: str
    feed_date: str
    next_publish_at: str


PUBLISH_START = time(9, 0, 0)
PRE_PUBLICATION_START = time(3, 0, 0)
KST = ZoneInfo('Asia/Seoul')


def resolve_home_feed_window(now: datetime) -> HomeFeedWindow:
    """Resolve the server-owned home feed publication window.

    Home feed is visible from 09:00:00 KST through next-day 02:59:59 KST.
    From 03:00:00 through 08:59:59 KST, today's feed is explicitly before publication.
    """
    now_kst = now.astimezone(KST) if now.tzinfo is not None else now.replace(tzinfo=KST)
    today = now_kst.date()
    current_time = now_kst.time().replace(microsecond=0)
    today_publish_at = datetime.combine(today, PUBLISH_START, tzinfo=KST)

    if current_time < PRE_PUBLICATION_START:
        return HomeFeedWindow(
            publication_status='published',
            feed_date=(today - timedelta(days=1)).isoformat(),
            next_publish_at=today_publish_at.isoformat(),
        )
    if current_time < PUBLISH_START:
        return HomeFeedWindow(
            publication_status='before_publication',
            feed_date=today.isoformat(),
            next_publish_at=today_publish_at.isoformat(),
        )
    return HomeFeedWindow(
        publication_status='published',
        feed_date=today.isoformat(),
        next_publish_at=(today_publish_at + timedelta(days=1)).isoformat(),
    )


def _current_home_feed_window() -> HomeFeedWindow:
    return resolve_home_feed_window(datetime.now(KST))


def _current_feed_date() -> str:
    """Return the KST product feed date served by the home feed."""
    return _current_home_feed_window().feed_date


@router.get(
    '/me/preference',
    response_model=UserPreferenceResponseSchema,
    summary='Get my onboarding preferences',
    description='Returns the authenticated user preference state used by frontend onboarding and feed filtering.',
    responses=AUTH_REQUIRED,
)
def get_my_preference(
    session: AuthSession = Depends(require_current_user),
    service: UserPreferenceService = Depends(get_user_preference_service),
):
    return UserPreferenceResponseSchema.from_entity(service.get_preferences(session.user_id))


@router.put(
    '/me/preference',
    response_model=UserPreferenceResponseSchema,
    summary='Update my onboarding preferences',
    description=(
        'Stores frontend onboarding preferences for the current user. wide mode requires 3~5 primary_categories '
        'and no subcategories. narrow mode requires exactly one primary category and at least one subcategory.'
    ),
    responses={**AUTH_REQUIRED, 422: {'description': 'Preference validation failed'}},
)
def put_my_preference(
    payload: UserPreferenceUpdateRequestSchema,
    session: AuthSession = Depends(require_current_user),
    service: UserPreferenceService = Depends(get_user_preference_service),
):
    return _update_my_preference(payload, session, service)


@router.patch(
    '/me/preference',
    response_model=UserPreferenceResponseSchema,
    summary='Update my interest categories',
    description=(
        'Updates the current user interest categories after onboarding. The request body uses the complete '
        'preference shape so mode, primary_categories, and subcategories can be validated together.'
    ),
    responses={**AUTH_REQUIRED, 422: {'description': 'Preference validation failed'}},
)
def patch_my_preference(
    payload: UserPreferenceUpdateRequestSchema,
    session: AuthSession = Depends(require_current_user),
    service: UserPreferenceService = Depends(get_user_preference_service),
):
    return _update_my_preference(payload, session, service)


def _update_my_preference(
    payload: UserPreferenceUpdateRequestSchema,
    session: AuthSession,
    service: UserPreferenceService,
) -> UserPreferenceResponseSchema:
    try:
        return UserPreferenceResponseSchema.from_entity(
            service.update_preferences(
                user_id=session.user_id,
                mode=payload.mode,
                primary_categories=payload.primary_categories,
                subcategories=payload.subcategories,
            )
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get(
    '/me/feed',
    response_model=FeedResponseSchema,
    summary='Get my snapshot-backed personalized feed',
    description=(
        'Returns the persisted daily feed snapshot for today\'s KST product feed date. Each article includes '
        'is_scrapped so frontend can render saved state without an additional scraps lookup. Opening the feed '
        'marks the snapshot viewed for check-in tracking.'
    ),
    responses={
        **AUTH_REQUIRED,
        425: {'description': 'Daily home feed has not reached the 09:00 KST publication window'},
    },
)
def get_my_feed(
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
    snapshot_service: DailyFeedSnapshotService = Depends(get_daily_feed_snapshot_service),
):
    assert session.user_id is not None
    window = _current_home_feed_window()
    if window.publication_status == 'before_publication':
        raise HTTPException(
            status_code=425,
            detail={
                'publication_status': window.publication_status,
                'feed_date': window.feed_date,
                'next_publish_at': window.next_publish_at,
            },
        )
    feed_date = window.feed_date
    try:
        snapshot = snapshot_service.generate_for_user_date(
            session.user_id,
            feed_date,
            generation_source='api:get_me_feed',
        )
        if snapshot.id is not None:
            snapshot = snapshot_service.mark_viewed(snapshot.id)
        return FeedResponseSchema.from_snapshot(snapshot, service, snapshot_service, session.user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get(
    '/me/archive',
    response_model=ArchiveMonthResponseSchema,
    summary='Get my monthly snapshot archive',
    description='Returns persisted daily feed snapshot metadata for the authenticated user in the requested YYYY-MM month.',
    responses=AUTH_REQUIRED,
)
def get_my_archive_month(
    month: str,
    session: AuthSession = Depends(require_current_user),
    snapshot_service: DailyFeedSnapshotService = Depends(get_daily_feed_snapshot_service),
):
    assert session.user_id is not None
    snapshots = snapshot_service.list_by_user_month(session.user_id, month)
    return ArchiveMonthResponseSchema.from_snapshots(session.user_id, month, snapshots, snapshot_service)


@router.get(
    '/me/archive/{archive_date}',
    response_model=ArchiveDateResponseSchema,
    summary='Get my daily snapshot archive',
    description='Returns the persisted daily feed snapshot items for the requested YYYY-MM-DD date and marks the snapshot viewed for check-in tracking.',
    responses={**AUTH_REQUIRED, 404: {'description': 'Daily feed snapshot not found'}},
)
def get_my_archive_date(
    archive_date: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
    snapshot_service: DailyFeedSnapshotService = Depends(get_daily_feed_snapshot_service),
):
    assert session.user_id is not None
    snapshot = snapshot_service.get_by_user_date(session.user_id, archive_date)
    if snapshot is None:
        raise HTTPException(status_code=404, detail='Daily feed snapshot not found')
    if snapshot.id is not None:
        snapshot = snapshot_service.mark_viewed(snapshot.id)
    return ArchiveDateResponseSchema.from_snapshot(snapshot, service, snapshot_service, session.user_id)
