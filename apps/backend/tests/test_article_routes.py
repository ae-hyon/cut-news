from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import Article, AuthSession
from app.domain.exceptions import NotFoundError
from app.presentation.api.dependencies import get_current_session, get_feed_service
from app.presentation.api.routes.articles import router


CURRENT_SESSION = AuthSession(
    user_id='user-kakao-123',
    session_state='onboarded',
    onboarding_completed=True,
    authenticated=True,
    auth_provider='kakao',
    provider_subject='kakao-123',
)


class StubFeedService:
    def get_article(self, article_id: str):
        if article_id == 'missing':
            raise NotFoundError('Article not found')
        return Article(
            id=article_id,
            title='Article title',
            summary='summary',
            content='full content',
            primary_category='tech',
            subcategory='ai',
            published_at='2026-04-15',
            original_url='https://example.com/article',
            score_weight=0.88,
        )

    def list_scraps(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return [self.get_article('A1')]


def build_client(session: AuthSession = CURRENT_SESSION) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_feed_service] = lambda: StubFeedService()
    app.dependency_overrides[get_current_session] = lambda: session
    return TestClient(app)


def test_public_article_detail_does_not_include_user_scrap_state():
    client = build_client()

    response = client.get('/v1/articles/A1')

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == 'A1'
    assert body['content'] == 'full content'
    assert body['is_scrapped'] is False


def test_me_article_detail_includes_current_users_scrap_state():
    client = build_client()

    response = client.get('/v1/me/articles/A1')

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == 'A1'
    assert body['is_scrapped'] is True


def test_me_article_detail_requires_authenticated_user():
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

    response = client.get('/v1/me/articles/A1')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'
