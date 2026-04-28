from __future__ import annotations

import pytest

from app.application.services.user_service import UserPreferenceService
from app.domain.entities import UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import ValidationError


class StubCategoryRepository:
    def __init__(self):
        self.primary = {'economy', 'politics', 'tech'}
        self.sub_map = {
            'economy': {'macro', 'real-estate'},
            'politics': {'election'},
            'tech': {'ai'},
        }

    def exists_by_slug(self, slug: str) -> bool:
        return slug in self.primary

    def valid_subcategories(self, category_slug: str) -> set[str]:
        return self.sub_map.get(category_slug, set())


class StubPreferenceRepository:
    def __init__(self):
        self.saved: UserPreference | None = None

    def get(self, user_id: str) -> UserPreference | None:
        return self.saved if self.saved and self.saved.user_id == user_id else None

    def save(self, preference: UserPreference) -> UserPreference:
        self.saved = preference
        return preference


@pytest.fixture
def service() -> UserPreferenceService:
    return UserPreferenceService(StubPreferenceRepository(), StubCategoryRepository())


def test_wide_mode_rejects_subcategories_payload(service: UserPreferenceService):
    with pytest.raises(ValidationError, match='wide mode does not accept subcategories'):
        service.update_preferences(
            user_id='demo-user',
            mode='wide',
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=['macro'],
        )


def test_wide_mode_rejects_duplicate_primary_categories(service: UserPreferenceService):
    with pytest.raises(ValidationError, match='primary categories must be unique'):
        service.update_preferences(
            user_id='demo-user',
            mode='wide',
            primary_categories=['economy', 'economy', 'tech'],
            subcategories=[],
        )


def test_narrow_mode_rejects_duplicate_subcategories(service: UserPreferenceService):
    with pytest.raises(ValidationError, match='subcategories must be unique'):
        service.update_preferences(
            user_id='demo-user',
            mode='narrow',
            primary_categories=['economy'],
            subcategories=['macro', 'macro'],
        )


def test_valid_narrow_preferences_complete_onboarding(service: UserPreferenceService):
    result = service.update_preferences(
        user_id='demo-user',
        mode='narrow',
        primary_categories=['economy'],
        subcategories=['macro', 'real-estate'],
    )

    assert result.mode is PreferenceMode.NARROW
    assert result.onboarding_completed is True
    assert result.subcategories == ['macro', 'real-estate']
