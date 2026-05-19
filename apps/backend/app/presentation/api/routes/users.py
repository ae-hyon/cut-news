from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.application.services.user_service import UserPreferenceService
from app.domain.entities import AuthSession
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import get_feed_service, get_user_preference_service, require_current_user
from app.presentation.schemas import (
    ArchiveDateResponseSchema,
    ArchiveMonthResponseSchema,
    FeedResponseSchema,
    UserPreferenceResponseSchema,
    UserPreferenceUpdateRequestSchema,
)

router = APIRouter(tags=['me'])

AUTH_REQUIRED = {401: {'description': 'Authentication required'}}


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
    summary='Get my personalized feed',
    description=(
        'Returns personalized feed blocks for the authenticated user. Each article includes is_scrapped so '
        'frontend can render saved state without an additional scraps lookup.'
    ),
    responses=AUTH_REQUIRED,
)
def get_my_feed(
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return FeedResponseSchema.from_payload(service.get_feed(session.user_id), service, session.user_id)


@router.get(
    '/me/archive',
    response_model=ArchiveMonthResponseSchema,
    summary='Get my monthly archive',
    description='Returns the authenticated user archive grouped by published date for the requested YYYY-MM month.',
    responses=AUTH_REQUIRED,
)
def get_my_archive_month(
    month: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    assert session.user_id is not None
    return ArchiveMonthResponseSchema.from_payload(service.get_archive_month(session.user_id, month), service, session.user_id)


@router.get(
    '/me/archive/{archive_date}',
    response_model=ArchiveDateResponseSchema,
    summary='Get my daily archive',
    description='Returns the authenticated user archive items for the requested YYYY-MM-DD date.',
    responses=AUTH_REQUIRED,
)
def get_my_archive_date(
    archive_date: str,
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    assert session.user_id is not None
    return ArchiveDateResponseSchema.from_payload(service.get_archive_date(session.user_id, archive_date), service, session.user_id)
