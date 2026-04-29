from __future__ import annotations

from app.application.services.feed_service import FeedService
from app.domain.entities import Article, UserPreference
from app.domain.enums import PreferenceMode


class StubArticleRepository:
    def __init__(self):
        self.all_articles = [
            Article(id='A1', title='e1', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://e', score_weight=0.80),
            Article(id='A2', title='e2', summary='s', content='c', primary_category='economy', subcategory='real-estate', published_at='2026-04-14', original_url='https://e', score_weight=0.95),
            Article(id='A3', title='p1', summary='s', content='c', primary_category='politics', subcategory='policy', published_at='2026-04-14', original_url='https://p', score_weight=0.70),
            Article(id='A4', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t', score_weight=0.88),
        ]
        self.by_primary = {
            'economy': [self.all_articles[0], self.all_articles[1]],
            'politics': [self.all_articles[2]],
            'tech': [self.all_articles[3]],
        }
        self.by_primary_and_subcategories = {
            ('economy', ('macro', 'real-estate')): [self.all_articles[0], self.all_articles[1]],
            ('economy', ('real-estate',)): [self.all_articles[1]],
        }

    def get_by_id(self, article_id: str):
        for article in self.all_articles:
            if article.id == article_id:
                return article
        return None

    def list_by_primary(self, slug: str):
        return list(self.by_primary.get(slug, []))

    def list_by_primary_and_subcategories(self, primary: str, subs: list[str]):
        return list(self.by_primary_and_subcategories.get((primary, tuple(subs)), []))

    def list_by_month(self, month: str):
        return [article for article in self.all_articles if article.published_at.startswith(month)]

    def list_by_date(self, archive_date: str):
        return [article for article in self.all_articles if article.published_at == archive_date]


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


def test_archive_month_respects_wide_primary_category_preferences():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.WIDE,
            primary_categories=['tech', 'economy'],
            subcategories=[],
            onboarding_completed=True,
        )
    )

    payload = service.list_archive_month('demo-user', '2026-04')

    assert list(payload) == ['2026-04-14', '2026-04-15']
    assert [article.id for article in payload['2026-04-14']] == ['A1', 'A2']
    assert [article.id for article in payload['2026-04-15']] == ['A4']


def test_archive_date_respects_narrow_subcategory_preferences():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.NARROW,
            primary_categories=['economy'],
            subcategories=['real-estate'],
            onboarding_completed=True,
        )
    )

    payload = service.list_archive_date('demo-user', '2026-04-14')

    assert [article.id for article in payload] == ['A2']
