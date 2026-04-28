from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.services.auth_service import AuthError

from app.presentation.api.dependencies import get_auth_service
from app.presentation.api.routes import auth


class StubAuthService:
    def start_kakao_auth(self) -> dict:
        return {
            'provider': 'kakao',
            'state': 'state-123',
            'authorization_url': 'https://kauth.kakao.com/oauth/authorize?client_id=test&state=state-123',
        }

    def complete_kakao_callback(self, code: str, state: str) -> dict:
        assert code == 'issued-code'
        assert state == 'state-123'
        return {
            'session': {
                'user_id': 'user-kakao-123',
                'session_state': 'authenticated',
                'onboarding_completed': False,
                'authenticated': True,
                'auth_provider': 'kakao',
                'provider_subject': 'kakao-123',
            },
            'access_token': 'access-token-123',
            'refresh_token': 'refresh-token-123',
            'token_type': 'bearer',
        }

    def resolve_session(
        self,
        user_id: str | None = None,
        provider: str | None = None,
        provider_subject: str | None = None,
        access_token: str | None = None,
    ) -> dict:
        if access_token == 'access-token-123' or (provider == 'kakao' and provider_subject == 'kakao-123'):
            return {
                'user_id': 'user-kakao-123',
                'session_state': 'authenticated',
                'onboarding_completed': False,
                'authenticated': True,
                'auth_provider': 'kakao',
                'provider_subject': 'kakao-123',
            }
        if user_id == 'demo-user':
            return {
                'user_id': 'demo-user',
                'session_state': 'onboarded',
                'onboarding_completed': True,
                'authenticated': False,
                'auth_provider': 'demo',
                'provider_subject': None,
            }
        return {
            'user_id': None,
            'session_state': 'anonymous',
            'onboarding_completed': False,
            'authenticated': False,
            'auth_provider': 'none',
            'provider_subject': None,
        }

    def refresh_session(self, refresh_token: str) -> dict:
        assert refresh_token == 'refresh-token-123'
        return {
            'session': {
                'user_id': 'user-kakao-123',
                'session_state': 'authenticated',
                'onboarding_completed': False,
                'authenticated': True,
                'auth_provider': 'kakao',
                'provider_subject': 'kakao-123',
            },
            'access_token': 'access-token-456',
            'refresh_token': 'refresh-token-456',
            'token_type': 'bearer',
        }

    def logout(self, refresh_token: str | None) -> None:
        assert refresh_token in (None, 'refresh-token-123', 'refresh-token-456')


class InvalidStateAuthService(StubAuthService):
    def complete_kakao_callback(self, code: str, state: str) -> dict:
        raise AuthError('invalid_oauth_state', 'OAuth state is invalid or expired.', status_code=401)


class KakaoFailureAuthService(StubAuthService):
    def complete_kakao_callback(self, code: str, state: str) -> dict:
        raise AuthError('kakao_token_exchange_failed', 'Kakao token exchange failed.', status_code=502)


def build_client(service: StubAuthService | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(auth.router, prefix='/v1')
    if service is not None:
        app.dependency_overrides[get_auth_service] = lambda: service
    return TestClient(app)


def test_auth_session_returns_anonymous_state_when_identity_missing():
    client = build_client(StubAuthService())

    response = client.get('/v1/auth/session')

    assert response.status_code == 200
    assert response.json() == {
        'user_id': None,
        'session_state': 'anonymous',
        'onboarding_completed': False,
        'authenticated': False,
        'auth_provider': 'none',
        'provider_subject': None,
    }


def test_auth_session_returns_onboarded_state_for_demo_user():
    client = build_client(StubAuthService())

    response = client.get('/v1/auth/session', params={'user_id': 'demo-user'})

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'demo-user',
        'session_state': 'onboarded',
        'onboarding_completed': True,
        'authenticated': False,
        'auth_provider': 'demo',
        'provider_subject': None,
    }


def test_kakao_start_returns_authorization_url_and_state():
    client = build_client(StubAuthService())

    response = client.get('/v1/auth/kakao/start')

    assert response.status_code == 200
    assert response.json() == {
        'provider': 'kakao',
        'state': 'state-123',
        'authorization_url': 'https://kauth.kakao.com/oauth/authorize?client_id=test&state=state-123',
    }


def test_kakao_callback_redirects_to_frontend_and_sets_jwt_cookies_for_new_user():
    client = build_client(StubAuthService())

    response = client.get('/v1/auth/kakao/callback', params={'code': 'issued-code', 'state': 'state-123'}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers['location'] == 'http://127.0.0.1:5173/?auth=kakao'
    set_cookie = response.headers.get('set-cookie', '')
    assert 'annoyingcap_access_token=' in set_cookie
    assert 'annoyingcap_refresh_token=' in set_cookie
    assert 'HttpOnly' in set_cookie


def test_auth_session_resolves_authenticated_user_from_access_cookie():
    client = build_client(StubAuthService())
    client.cookies.set('annoyingcap_access_token', 'access-token-123')

    response = client.get('/v1/auth/session')

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'user-kakao-123',
        'session_state': 'authenticated',
        'onboarding_completed': False,
        'authenticated': True,
        'auth_provider': 'kakao',
        'provider_subject': 'kakao-123',
    }


def test_auth_session_resolves_authenticated_user_from_provider_subject():
    client = build_client(StubAuthService())

    response = client.get('/v1/auth/session', params={'provider': 'kakao', 'provider_subject': 'kakao-123'})

    assert response.status_code == 200
    assert response.json()['user_id'] == 'user-kakao-123'
    assert response.json()['authenticated'] is True


def test_auth_refresh_rotates_cookies_and_returns_session_payload():
    client = build_client(StubAuthService())
    client.cookies.set('annoyingcap_refresh_token', 'refresh-token-123')

    response = client.post('/v1/auth/refresh')

    assert response.status_code == 200
    assert response.json()['user_id'] == 'user-kakao-123'
    set_cookie = response.headers.get('set-cookie', '')
    assert 'annoyingcap_access_token=access-token-456' in set_cookie
    assert 'annoyingcap_refresh_token=refresh-token-456' in set_cookie


def test_auth_logout_clears_auth_cookies():
    client = build_client(StubAuthService())
    client.cookies.set('annoyingcap_refresh_token', 'refresh-token-123')

    response = client.post('/v1/auth/logout')

    assert response.status_code == 200
    assert response.json() == {'ok': True}
    set_cookie = response.headers.get('set-cookie', '')
    assert 'annoyingcap_access_token=""' in set_cookie
    assert 'annoyingcap_refresh_token=""' in set_cookie


def test_kakao_callback_returns_401_for_invalid_state():
    client = build_client(InvalidStateAuthService())

    response = client.get('/v1/auth/kakao/callback', params={'code': 'issued-code', 'state': 'tampered-state'}, follow_redirects=False)

    assert response.status_code == 401
    assert response.json() == {
        'code': 'invalid_oauth_state',
        'message': 'OAuth state is invalid or expired.',
    }


def test_kakao_callback_returns_502_for_kakao_exchange_failure():
    client = build_client(KakaoFailureAuthService())

    response = client.get('/v1/auth/kakao/callback', params={'code': 'issued-code', 'state': 'state-123'}, follow_redirects=False)

    assert response.status_code == 502
    assert response.json() == {
        'code': 'kakao_token_exchange_failed',
        'message': 'Kakao token exchange failed.',
    }


def test_auth_session_user_id_query_ignores_stale_access_cookie_after_onboarding_write():
    client = build_client(StubAuthService())
    client.cookies.set('annoyingcap_access_token', 'access-token-123')

    response = client.get('/v1/auth/session', params={'user_id': 'demo-user'})

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'demo-user',
        'session_state': 'onboarded',
        'onboarding_completed': True,
        'authenticated': False,
        'auth_provider': 'demo',
        'provider_subject': None,
    }


def test_auth_session_returns_onboarded_state_for_authenticated_kakao_user_after_onboarding():
    class OnboardedKakaoAuthService(StubAuthService):
        def complete_kakao_callback(self, code: str, state: str) -> dict:
            return {
                'session': {
                    'user_id': 'user-kakao-123',
                    'session_state': 'onboarded',
                    'onboarding_completed': True,
                    'authenticated': True,
                    'auth_provider': 'kakao',
                    'provider_subject': 'kakao-123',
                },
                'access_token': 'access-token-123',
                'refresh_token': 'refresh-token-123',
                'token_type': 'bearer',
            }

        def resolve_session(self, user_id=None, provider=None, provider_subject=None, access_token=None):
            return {
                'user_id': 'user-kakao-123',
                'session_state': 'onboarded',
                'onboarding_completed': True,
                'authenticated': True,
                'auth_provider': 'kakao',
                'provider_subject': 'kakao-123',
            }

    client = build_client(OnboardedKakaoAuthService())
    callback_response = client.get('/v1/auth/kakao/callback', params={'code': 'issued-code', 'state': 'state-123'}, follow_redirects=False)
    assert callback_response.status_code == 302
    assert callback_response.headers['location'] == 'http://127.0.0.1:5173/?auth=kakao'

    client.cookies.set('annoyingcap_access_token', 'access-token-123')
    response = client.get('/v1/auth/session')

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'user-kakao-123',
        'session_state': 'onboarded',
        'onboarding_completed': True,
        'authenticated': True,
        'auth_provider': 'kakao',
        'provider_subject': 'kakao-123',
    }
