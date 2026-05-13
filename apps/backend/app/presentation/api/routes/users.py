from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.application.services.user_service import UserPreferenceService
from app.domain.entities import AuthSession
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import get_feed_service, get_user_preference_service, require_current_user
from app.presentation.schemas import (
    FeedResponseSchema,
    UserPreferenceResponseSchema,
    UserPreferenceUpdateRequestSchema,
)

router = APIRouter(tags=['me'])


@router.get('/me/preference', response_model=UserPreferenceResponseSchema)
def get_my_preference(
    session: AuthSession = Depends(require_current_user),
    service: UserPreferenceService = Depends(get_user_preference_service),
):
    return UserPreferenceResponseSchema.from_entity(service.get_preferences(session.user_id))


@router.put('/me/preference', response_model=UserPreferenceResponseSchema)
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


@router.get('/me/feed', response_model=FeedResponseSchema)
def get_my_feed(
    session: AuthSession = Depends(require_current_user),
    service: FeedService = Depends(get_feed_service),
):
    return FeedResponseSchema.from_payload(service.get_feed(session.user_id), service, session.user_id)
