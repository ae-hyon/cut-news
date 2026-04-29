from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import Article
from app.presentation.api.dependencies import get_feed_service
from app.presentation.api.routes.scraps import router


class StubFeedService:
    def __init__(self):
        self.scrapped_ids: list[str] = ['A3', 'A4']

    def list_scraps(self, user_id: str):
        return [
            Article(id='A3', title='p1', summary='s', content='c', primary_category='politics', subcategory='policy', published_at='2026-04-14', original_url='https://p', score_weight=0.70),
            Article(id='A4', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t', score_weight=0.88),
        ]

    def add_scrap(self, user_id: str, article_id: str):
        if article_id not in self.scrapped_ids:
            self.scrapped_ids.append(article_id)

    def remove_scrap(self, user_id: str, article_id: str):
        self.scrapped_ids = [item for item in self.scrapped_ids if item != article_id]


stub_service = StubFeedService()


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_feed_service] = lambda: stub_service
    return TestClient(app)


def test_scrap_toggle_endpoints_report_scrapped_state_without_preference_filtering():
    client = build_client()

    add_response = client.put('/v1/users/demo-user/scraps/A1')
    assert add_response.status_code == 200
    assert add_response.json() == {'user_id': 'demo-user', 'article_id': 'A1', 'scrapped': True}

    remove_response = client.delete('/v1/users/demo-user/scraps/A1')
    assert remove_response.status_code == 200
    assert remove_response.json() == {'user_id': 'demo-user', 'article_id': 'A1', 'scrapped': False}
