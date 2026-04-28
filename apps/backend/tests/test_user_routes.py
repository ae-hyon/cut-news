from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import get_user_preference_service
from app.presentation.api.routes.users import router


class StubUserPreferenceService:
    def get_preferences(self, user_id: str) -> UserPreference:
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=False,
        )

    def update_preferences(self, user_id: str, mode: str, primary_categories: list[str], subcategories: list[str]) -> UserPreference:
        if mode == 'wide' and subcategories:
            raise ValidationError('wide mode does not accept subcategories')
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode(mode),
            primary_categories=primary_categories,
            subcategories=subcategories,
            onboarding_completed=True,
        )


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_user_preference_service] = lambda: StubUserPreferenceService()
    return TestClient(app)


def test_put_user_preferences_returns_422_for_invalid_onboarding_payload():
    client = build_client()

    response = client.put(
        '/v1/users/demo-user/preferences',
        json={
            'mode': 'wide',
            'primary_categories': ['economy', 'politics', 'tech'],
            'subcategories': ['macro'],
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'] == 'wide mode does not accept subcategories'


def test_put_user_preferences_marks_onboarding_completed_when_valid():
    client = build_client()

    response = client.put(
        '/v1/users/demo-user/preferences',
        json={
            'mode': 'narrow',
            'primary_categories': ['economy'],
            'subcategories': ['macro', 'real-estate'],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['mode'] == 'narrow'
    assert body['onboarding_completed'] is True
    assert body['subcategories'] == ['macro', 'real-estate']
