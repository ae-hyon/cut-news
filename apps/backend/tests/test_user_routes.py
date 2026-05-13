from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import AuthSession, UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import get_current_session, get_user_preference_service
from app.presentation.api.routes.users import router


CURRENT_SESSION = AuthSession(
    user_id='user-kakao-123',
    session_state='authenticated',
    onboarding_completed=False,
    authenticated=True,
    auth_provider='kakao',
    provider_subject='kakao-123',
)


class StubUserPreferenceService:
    def get_preferences(self, user_id: str) -> UserPreference:
        assert user_id == 'user-kakao-123'
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=False,
        )

    def update_preferences(self, user_id: str, mode: str, primary_categories: list[str], subcategories: list[str]) -> UserPreference:
        assert user_id == 'user-kakao-123'
        if mode == 'wide' and subcategories:
            raise ValidationError('wide mode does not accept subcategories')
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode(mode),
            primary_categories=primary_categories,
            subcategories=subcategories,
            onboarding_completed=True,
        )


def build_client(session: AuthSession = CURRENT_SESSION) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_user_preference_service] = lambda: StubUserPreferenceService()
    app.dependency_overrides[get_current_session] = lambda: session
    return TestClient(app)


def test_get_me_preference_returns_current_users_preference():
    client = build_client()

    response = client.get('/v1/me/preference')

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'user-kakao-123',
        'mode': 'wide',
        'primary_categories': ['economy', 'politics', 'tech'],
        'subcategories': [],
        'onboarding_completed': False,
    }


def test_put_me_preference_returns_422_for_invalid_onboarding_payload():
    client = build_client()

    response = client.put(
        '/v1/me/preference',
        json={
            'mode': 'wide',
            'primary_categories': ['economy', 'politics', 'tech'],
            'subcategories': ['macro'],
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'] == 'wide mode does not accept subcategories'


def test_put_me_preference_marks_onboarding_completed_when_valid():
    client = build_client()

    response = client.put(
        '/v1/me/preference',
        json={
            'mode': 'narrow',
            'primary_categories': ['economy'],
            'subcategories': ['macro', 'real-estate'],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['mode'] == 'narrow'
    assert body['onboarding_completed'] is True
    assert body['subcategories'] == ['macro', 'real-estate']


def test_me_preference_requires_authenticated_user():
    client = build_client(
        AuthSession(
            user_id=None,
            session_state='anonymous',
            onboarding_completed=False,
            authenticated=False,
            auth_provider='none',
            provider_subject=None,
        )
    )

    response = client.get('/v1/me/preference')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'
