from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import Article, AuthSession
from app.presentation.api.dependencies import get_current_session, get_feed_service
from app.presentation.api.routes.scraps import router


CURRENT_SESSION = AuthSession(
    user_id='user-kakao-123',
    session_state='onboarded',
    onboarding_completed=True,
    authenticated=True,
    auth_provider='kakao',
    provider_subject='kakao-123',
)


class StubFeedService:
    def __init__(self):
        self.scrapped_ids: list[str] = ['A3', 'A4']

    def list_scraps(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return [
            Article(id='A3', title='p1', summary='s', content='c', primary_category='politics', subcategory='policy', published_at='2026-04-14', original_url='https://p', score_weight=0.70),
            Article(id='A4', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t', score_weight=0.88),
        ]

    def add_scrap(self, user_id: str, article_id: str):
        assert user_id == 'user-kakao-123'
        if article_id not in self.scrapped_ids:
            self.scrapped_ids.append(article_id)

    def remove_scrap(self, user_id: str, article_id: str):
        assert user_id == 'user-kakao-123'
        self.scrapped_ids = [item for item in self.scrapped_ids if item != article_id]


stub_service = StubFeedService()


def build_client(session: AuthSession = CURRENT_SESSION) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_feed_service] = lambda: stub_service
    app.dependency_overrides[get_current_session] = lambda: session
    return TestClient(app)


def test_me_scraps_lists_current_users_scraps_without_preference_filtering():
    client = build_client()

    response = client.get('/v1/me/scraps')

    assert response.status_code == 200
    assert response.json()['user_id'] == 'user-kakao-123'
    assert [item['id'] for item in response.json()['items']] == ['A3', 'A4']
    assert all(item['is_scrapped'] is True for item in response.json()['items'])


def test_me_scrap_membership_endpoints_report_scrapped_state():
    client = build_client()

    add_response = client.put('/v1/me/scraps/A1')
    assert add_response.status_code == 200
    assert add_response.json() == {'user_id': 'user-kakao-123', 'article_id': 'A1', 'scrapped': True}

    remove_response = client.delete('/v1/me/scraps/A1')
    assert remove_response.status_code == 200
    assert remove_response.json() == {'user_id': 'user-kakao-123', 'article_id': 'A1', 'scrapped': False}


def test_me_scraps_requires_authenticated_user():
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

    response = client.get('/v1/me/scraps')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'
