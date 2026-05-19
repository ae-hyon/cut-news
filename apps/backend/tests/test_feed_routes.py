from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import Article, AuthSession
from app.presentation.api.dependencies import get_current_session, get_feed_service
from app.presentation.api.routes.users import router


CURRENT_SESSION = AuthSession(
    user_id='user-kakao-123',
    session_state='onboarded',
    onboarding_completed=True,
    authenticated=True,
    auth_provider='kakao',
    provider_subject='kakao-123',
)


class StubFeedService:
    def get_feed(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return {
            'user_id': user_id,
            'mode': 'wide',
            'blocks': [
                {
                    'key': 'tech-block',
                    'title': 'tech block',
                    'weight': 1.0,
                    'articles': [
                        Article(id='A1', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t/1', score_weight=0.88),
                    ],
                }
            ],
        }

    def list_scraps(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return [Article(id='A1', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t/1', score_weight=0.88)]

    def get_archive_month(self, user_id: str, archive_month: str):
        assert user_id == 'user-kakao-123'
        assert archive_month == '2026-04'
        return {
            'user_id': user_id,
            'month': archive_month,
            'days': [
                {
                    'date': '2026-04-15',
                    'count': 1,
                    'items': [
                        Article(id='A1', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t/1', score_weight=0.88),
                    ],
                }
            ],
        }

    def get_archive_date(self, user_id: str, archive_date: str):
        assert user_id == 'user-kakao-123'
        assert archive_date == '2026-04-15'
        return {
            'user_id': user_id,
            'date': archive_date,
            'items': [
                Article(id='A1', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t/1', score_weight=0.88),
            ],
        }


def build_client(session: AuthSession = CURRENT_SESSION) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_feed_service] = lambda: StubFeedService()
    app.dependency_overrides[get_current_session] = lambda: session
    return TestClient(app)


def test_me_feed_returns_current_users_feed():
    client = build_client()

    response = client.get('/v1/me/feed')

    assert response.status_code == 200
    assert response.json()['user_id'] == 'user-kakao-123'
    assert response.json()['blocks'][0]['articles'][0]['id'] == 'A1'


def test_me_feed_requires_authenticated_user():
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

    response = client.get('/v1/me/feed')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'


def test_me_archive_month_returns_current_users_calendar_items():
    client = build_client()

    response = client.get('/v1/me/archive?month=2026-04')

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['month'] == '2026-04'
    assert body['days'][0]['date'] == '2026-04-15'
    assert body['days'][0]['count'] == 1
    assert body['days'][0]['items'][0]['id'] == 'A1'
    assert body['days'][0]['items'][0]['is_scrapped'] is True


def test_me_archive_date_returns_current_users_daily_items():
    client = build_client()

    response = client.get('/v1/me/archive/2026-04-15')

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['date'] == '2026-04-15'
    assert body['items'][0]['id'] == 'A1'
    assert body['items'][0]['is_scrapped'] is True


def test_me_archive_requires_authenticated_user():
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

    response = client.get('/v1/me/archive?month=2026-04')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'
