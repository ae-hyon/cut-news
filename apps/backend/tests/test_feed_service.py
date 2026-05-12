from __future__ import annotations

from app.application.services.feed_service import FeedService
from app.domain.entities import Article, UserPreference
from app.domain.enums import PreferenceMode


class StubArticleRepository:
    def __init__(self):
        self.all_articles = [
            Article(id='A1', title='e1', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://e/1', score_weight=0.80),
            Article(id='A2', title='e2', summary='s', content='c', primary_category='economy', subcategory='real-estate', published_at='2026-04-14', original_url='https://e/2', score_weight=0.95),
            Article(id='A3', title='p1', summary='s', content='c', primary_category='politics', subcategory='policy', published_at='2026-04-14', original_url='https://p', score_weight=0.70),
            Article(id='A4', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t', score_weight=0.88),
            Article(id='A5', title='e3', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-15', original_url='https://e/3', score_weight=0.94),
            Article(id='A6', title='e4', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-13', original_url='https://e/4', score_weight=0.60),
            Article(id='A7', title='e5', summary='s', content='c', primary_category='economy', subcategory='inflation', published_at='2026-04-15', original_url='https://e/5', score_weight=0.89),
        ]
        self.by_primary = {
            'economy': [self.all_articles[0], self.all_articles[1], self.all_articles[4], self.all_articles[5], self.all_articles[6]],
            'politics': [self.all_articles[2]],
            'tech': [self.all_articles[3]],
        }
        self.by_primary_and_subcategories = {
            ('economy', ('macro', 'real-estate')): [self.all_articles[0], self.all_articles[1], self.all_articles[4], self.all_articles[5]],
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
    def __init__(self, article_ids: list[str] | None = None):
        self.article_ids = list(article_ids or [])

    def list_article_ids(self, user_id: str):
        return list(self.article_ids)

    def add(self, user_id: str, article_id: str):
        if article_id not in self.article_ids:
            self.article_ids.append(article_id)
        return None

    def remove(self, user_id: str, article_id: str):
        self.article_ids = [item for item in self.article_ids if item != article_id]
        return None


def build_service(preference: UserPreference | None, scrap_ids: list[str] | None = None) -> FeedService:
    return FeedService(StubArticleRepository(), StubPreferenceRepository(preference), StubScrapRepository(scrap_ids))


def build_service_with_article_repository(article_repository: StubArticleRepository, preference: UserPreference | None, scrap_ids: list[str] | None = None) -> FeedService:
    return FeedService(article_repository, StubPreferenceRepository(preference), StubScrapRepository(scrap_ids))


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


def test_wide_feed_sorts_articles_by_importance_score_without_recency_boost():
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

    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A5', 'A7', 'A1']


def test_narrow_feed_fills_same_primary_articles_when_selected_subcategories_are_short():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.NARROW,
            primary_categories=['economy'],
            subcategories=['real-estate'],
            onboarding_completed=True,
        )
    )

    payload = service.get_feed('demo-user')

    assert payload['mode'] == 'narrow'
    assert len(payload['blocks']) == 1
    assert payload['blocks'][0]['key'] == 'economy-focus'
    assert payload['blocks'][0]['weight'] == 1.0
    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A5', 'A7', 'A1']


def test_wide_feed_returns_up_to_four_articles_per_block():
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

    assert len(payload['blocks'][0]['articles']) == 4


def test_same_day_articles_still_sort_by_score_weight_descending():
    articles = [
        Article(id='S1', title='s1', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://s/1', score_weight=0.80),
        Article(id='S2', title='s2', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://s/2', score_weight=0.95),
        Article(id='S3', title='s3', summary='s', content='c', primary_category='economy', subcategory='macro', published_at='2026-04-14', original_url='https://s/3', score_weight=0.88),
    ]

    assert [article.id for article in FeedService._sort_articles(articles)] == ['S2', 'S3', 'S1']


def test_dedupe_articles_drops_lower_ranked_near_duplicate_titles_on_same_day():
    articles = [
        Article(id='D1', title='현대차 중국 전략형 아이오닉V 베이징 모터쇼서 세계 최초 공개', summary='s', content='c', primary_category='sectors', subcategory='mobility', published_at='2026-04-24', original_url='https://d/1', score_weight=0.82),
        Article(id='D2', title='현대차, 베이징모터쇼서 중국전략형 아이오닉V 세계 최초 공개', summary='s', content='c', primary_category='sectors', subcategory='mobility', published_at='2026-04-24', original_url='https://d/2', score_weight=0.72),
        Article(id='D3', title='현대차 전기차 생산 확대', summary='s', content='c', primary_category='sectors', subcategory='mobility', published_at='2026-04-24', original_url='https://d/3', score_weight=0.70),
    ]

    ranked = FeedService._sort_articles(articles)

    assert [article.id for article in FeedService._dedupe_articles(ranked)] == ['D1', 'D3']


def test_wide_feed_excludes_articles_below_minimum_score_threshold():
    article_repository = StubArticleRepository()
    article_repository.by_primary['economy'] = [
        article_repository.all_articles[4],
        article_repository.all_articles[1],
        article_repository.all_articles[6],
        Article(
            id='A8',
            title='e6',
            summary='s',
            content='c',
            primary_category='economy',
            subcategory='macro',
            published_at='2026-04-15',
            original_url='https://e/6',
            score_weight=0.64,
        ),
    ]
    service = build_service_with_article_repository(
        article_repository,
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy'],
            subcategories=[],
            onboarding_completed=True,
        ),
    )

    payload = service.get_feed('demo-user')

    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A5', 'A7']


def test_narrow_feed_does_not_backfill_with_articles_below_minimum_score_threshold():
    article_repository = StubArticleRepository()
    article_repository.by_primary_and_subcategories[('economy', ('real-estate',))] = [article_repository.all_articles[1]]
    article_repository.by_primary['economy'] = [
        article_repository.all_articles[1],
        article_repository.all_articles[4],
        article_repository.all_articles[6],
        Article(
            id='A8',
            title='e6',
            summary='s',
            content='c',
            primary_category='economy',
            subcategory='macro',
            published_at='2026-04-15',
            original_url='https://e/6',
            score_weight=0.64,
        ),
    ]
    service = build_service_with_article_repository(
        article_repository,
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.NARROW,
            primary_categories=['economy'],
            subcategories=['real-estate'],
            onboarding_completed=True,
        ),
    )

    payload = service.get_feed('demo-user')

    assert [article.id for article in payload['blocks'][0]['articles']] == ['A2', 'A5', 'A7']


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

    assert list(payload) == ['2026-04-13', '2026-04-14', '2026-04-15']
    assert [article.id for article in payload['2026-04-14']] == ['A1', 'A2']
    assert [article.id for article in payload['2026-04-15']] == ['A4', 'A5', 'A7']


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


def test_scraps_remain_available_even_when_current_preference_would_filter_them_out():
    service = build_service(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.NARROW,
            primary_categories=['economy'],
            subcategories=['real-estate'],
            onboarding_completed=True,
        ),
        scrap_ids=['A3', 'A4'],
    )

    payload = service.list_scraps('demo-user')

    assert [article.id for article in payload] == ['A3', 'A4']
