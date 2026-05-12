from fastapi import APIRouter, Depends, HTTPException

from app.application.services.feed_service import FeedService
from app.application.services.user_service import UserPreferenceService
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import get_feed_service, get_user_preference_service
from app.presentation.schemas import (
    FeedResponseSchema,
    ScrapListResponseSchema,
    ScrapToggleResponseSchema,
    UserPreferenceResponseSchema,
    UserPreferenceUpdateRequestSchema,
)

router = APIRouter(tags=['users'])


@router.get('/users/{user_id}/preferences', response_model=UserPreferenceResponseSchema)
def get_user_preferences(user_id: str, service: UserPreferenceService = Depends(get_user_preference_service)):
    return UserPreferenceResponseSchema.from_entity(service.get_preferences(user_id))


@router.put('/users/{user_id}/preferences', response_model=UserPreferenceResponseSchema)
def put_user_preferences(user_id: str, payload: UserPreferenceUpdateRequestSchema, service: UserPreferenceService = Depends(get_user_preference_service)):
    try:
        return UserPreferenceResponseSchema.from_entity(
            service.update_preferences(
                user_id=user_id,
                mode=payload.mode,
                primary_categories=payload.primary_categories,
                subcategories=payload.subcategories,
            )
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.get('/users/{user_id}/feed', response_model=FeedResponseSchema)
def get_user_feed(user_id: str, service: FeedService = Depends(get_feed_service)):
    return FeedResponseSchema.from_payload(service.get_feed(user_id), service, user_id)


@router.get('/users/{user_id}/scraps', response_model=ScrapListResponseSchema)
def get_user_scraps(user_id: str, service: FeedService = Depends(get_feed_service)):
    return ScrapListResponseSchema.from_entities(user_id, service.list_scraps(user_id), service)
