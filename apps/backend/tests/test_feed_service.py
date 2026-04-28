from __future__ import annotations

from app.application.services.feed_service import FeedService
from app.domain.entities import Article, UserPreference
from app.domain.enums import PreferenceMode


class StubArticleRepository:
    def __init__(self):
        self.by_primary = {
            'economy': [
                Article(id='A1', title='e1', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://e', score_weight=0.80),
                Article(id='A2', title='e2', summary='s', content='c', primary_category='economy', subcategory='real-estate', published_at='2026-04-14', original_url='https://e', score_weight=0.95),
            ],
            'politics': [
                Article(id='A3', title='p1', summary='s', content='c', primary_category='politics', subcategory='policy', published_at='2026-04-14', original_url='https://p', score_weight=0.70),
            ],
            'tech': [
                Article(id='A4', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-14', original_url='https://t', score_weight=0.88),
            ],
        }
        self.by_primary_and_subcategories = {
            ('economy', ('macro', 'real-estate')): [
                Article(id='A1', title='e1', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://e', score_weight=0.80),
                Article(id='A2', title='e2', summary='s', content='c', primary_category='economy', subcategory='real-estate', published_at='2026-04-14', original_url='https://e', score_weight=0.95),
            ]
        }

    def get_by_id(self, article_id: str):
        return None

    def list_by_primary(self, slug: str):
        return list(self.by_primary.get(slug, []))

    def list_by_primary_and_subcategories(self, primary: str, subs: list[str]):
        return list(self.by_primary_and_subcategories.get((primary, tuple(subs)), []))

    def list_by_month(self, month: str):
        return []

    def list_by_date(self, archive_date: str):
        return []


class StubPreferenceRepository:
    def __init__(self, preference: UserPreference | None):
        self.preference = preference

    def get(self, user_id: str):
        return self.preference

    def save(self, preference: UserPreference):
        self.preference = preference
        return preference


class StubScrapRepository:
    def list_article_ids(self, user_id: str):
        return []

    def add(self, user_id: str, article_id: str):
        return None

    def remove(self, user_id: str, article_id: str):
        return None


def build_service(preference: UserPreference | None) -> FeedService:
    return FeedService(StubArticleRepository(), StubPreferenceRepository(preference), StubScrapRepository())


def test_wide_feed_preserves_preference_order_and_descending_weights():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.WIDE,
            primary_categories=['tech', 'economy', 'politics'],
            subcategories=[],
            onboarding_completed=True,
        )
    )

    payload = service.get_feed('demo-user')

    assert [block['key'] for block in payload['blocks']] == ['tech-block', 'economy-block', 'politics-block']
    assert [block['weight'] for block in payload['blocks']] == [1.0, 0.85, 0.7]


def test_wide_feed_sorts_articles_by_score_weight_descending_inside_each_block():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'tech', 'politics'],
            subcategories=[],
            onboarding_completed=True,
        )
    )

    payload = service.get_feed('demo-user')

    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A1']


def test_narrow_feed_returns_single_focus_block_with_full_weight_and_sorted_articles():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.NARROW,
            primary_categories=['economy'],
            subcategories=['macro', 'real-estate'],
            onboarding_completed=True,
        )
    )

    payload = service.get_feed('demo-user')

    assert payload['mode'] == 'narrow'
    assert len(payload['blocks']) == 1
    assert payload['blocks'][0]['key'] == 'economy-focus'
    assert payload['blocks'][0]['weight'] == 1.0
    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A1']
