from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.daily_feed_snapshot_service import DailyFeedSnapshotService
from app.domain.entities import Article, DailyFeedSnapshot, DailyFeedSnapshotItem, UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import NotFoundError


class StubPreferenceRepository:
    def __init__(self, preference: UserPreference | None):
        self.preference = preference

    def get(self, user_id: str) -> UserPreference | None:
        return self.preference

    def save(self, preference: UserPreference) -> UserPreference:
        self.preference = preference
        return preference


class StubFeedService:
    def __init__(self):
        self.blocks = [
            {
                'key': 'tech-block',
                'title': 'tech block',
                'weight': 1.0,
                'articles': [
                    Article(
                        id='A2',
                        title='기술 뉴스',
                        summary='s',
                        content='c',
                        primary_category='tech',
                        subcategory='ai',
                        published_at='2026-05-20',
                        original_url='https://news.example/a2',
                        score_weight=0.88,
                    ),
                ],
            },
            {
                'key': 'economy-block',
                'title': 'economy block',
                'weight': 0.85,
                'articles': [
                    Article(
                        id='A1',
                        title='경제 뉴스',
                        summary='s',
                        content='c',
                        primary_category='economy',
                        subcategory='macro',
                        published_at='2026-05-20',
                        original_url='https://news.example/a1',
                        score_weight=0.95,
                    ),
                ],
            },
        ]
        self.article_by_id = {
            article.id: article
            for block in self.blocks
            for article in block.get('articles', [])
        }
        self.calls: list[tuple[PreferenceMode, list[str], list[str], str | None]] = []

    def build_feed_blocks_for_preference(
        self,
        mode: PreferenceMode,
        primary_categories: list[str],
        subcategories: list[str],
        published_date: str | None = None,
    ) -> list[dict]:
        self.calls.append((mode, list(primary_categories), list(subcategories), published_date))
        return self.blocks

    def get_article(self, article_id: str) -> Article:
        article = self.article_by_id.get(article_id)
        if article is None:
            raise NotFoundError('Article not found')
        return article


class StubSnapshotRepository:
    def __init__(self):
        self.snapshots: dict[tuple[str, str], DailyFeedSnapshot] = {}
        self.next_id = 1

    def get_by_id(self, snapshot_id: int) -> DailyFeedSnapshot | None:
        for snapshot in self.snapshots.values():
            if snapshot.id == snapshot_id:
                return snapshot.model_copy(deep=True)
        return None

    def get_by_user_date(self, user_id: str, feed_date: str) -> DailyFeedSnapshot | None:
        snapshot = self.snapshots.get((user_id, feed_date))
        return snapshot.model_copy(deep=True) if snapshot else None

    def list_by_user_month(self, user_id: str, month: str) -> list[DailyFeedSnapshot]:
        return [
            snapshot.model_copy(deep=True)
            for (snapshot_user_id, feed_date), snapshot in self.snapshots.items()
            if snapshot_user_id == user_id and feed_date.startswith(f'{month}-')
        ]

    def save(self, snapshot: DailyFeedSnapshot) -> DailyFeedSnapshot:
        key = (snapshot.user_id, snapshot.feed_date)
        existing = self.snapshots.get(key)
        saved = snapshot.model_copy(deep=True)
        saved.id = existing.id if existing else self.next_id
        if existing is None:
            self.next_id += 1
        for item in saved.items:
            item.snapshot_id = saved.id
        self.snapshots[key] = saved
        return saved.model_copy(deep=True)

    def replace_items(self, snapshot_id: int, items):
        raise AssertionError('save should replace items atomically in service tests')

    def mark_viewed(self, snapshot_id: int, viewed_at: datetime) -> DailyFeedSnapshot:
        for key, snapshot in self.snapshots.items():
            if snapshot.id == snapshot_id:
                updated = snapshot.model_copy(deep=True)
                if updated.first_viewed_at is None:
                    updated.first_viewed_at = viewed_at
                if updated.status == 'generated':
                    updated.status = 'viewed'
                self.snapshots[key] = updated
                return updated.model_copy(deep=True)
        raise ValueError('Daily feed snapshot not found')


class StubReadRepository:
    def __init__(self):
        self.reads: list[tuple[str, str, int | None, datetime, str | None]] = []

    def mark_read(self, user_id: str, article_id: str, snapshot_id: int | None, read_at: datetime, read_source: str | None = None) -> None:
        self.reads.append((user_id, article_id, snapshot_id, read_at, read_source))

    def list_read_article_ids(self, user_id: str, snapshot_id: int) -> set[str]:
        return {article_id for read_user_id, article_id, read_snapshot_id, *_ in self.reads if read_user_id == user_id and read_snapshot_id == snapshot_id}


def build_preference(mode: PreferenceMode = PreferenceMode.WIDE, primary_categories: list[str] | None = None, subcategories: list[str] | None = None) -> UserPreference:
    return UserPreference(
        user_id='demo-user',
        mode=mode,
        primary_categories=primary_categories or ['tech', 'economy'],
        subcategories=subcategories or [],
        onboarding_completed=True,
    )


def build_service(
    preference: UserPreference | None = None,
    snapshot_repository: StubSnapshotRepository | None = None,
    feed_service: StubFeedService | None = None,
) -> tuple[DailyFeedSnapshotService, StubPreferenceRepository, StubFeedService, StubSnapshotRepository, StubReadRepository]:
    preference_repository = StubPreferenceRepository(preference or build_preference())
    feed_service = feed_service or StubFeedService()
    snapshot_repository = snapshot_repository or StubSnapshotRepository()
    read_repository = StubReadRepository()
    service = DailyFeedSnapshotService(
        feed_service=feed_service,
        preference_repository=preference_repository,
        snapshot_repository=snapshot_repository,
        read_repository=read_repository,
        clock=lambda: datetime(2026, 5, 20, 0, 30, tzinfo=UTC),
    )
    return service, preference_repository, feed_service, snapshot_repository, read_repository


def test_generate_for_user_date_saves_preference_and_feed_block_items():
    service, _preference_repository, feed_service, _snapshot_repository, _read_repository = build_service()

    snapshot = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='manual-test')

    assert snapshot.id == 1
    assert snapshot.user_id == 'demo-user'
    assert snapshot.feed_date == '2026-05-20'
    assert snapshot.status == 'generated'
    assert snapshot.generated_at == datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    assert snapshot.preference_mode == PreferenceMode.WIDE
    assert snapshot.primary_categories == ['tech', 'economy']
    assert snapshot.subcategories == []
    assert snapshot.generation_source == 'manual-test'
    assert feed_service.calls == [(PreferenceMode.WIDE, ['tech', 'economy'], [], '2026-05-20')]
    assert [(item.article_id, item.block_key, item.block_title, item.sort_order, item.score_weight) for item in snapshot.items] == [
        ('A2', 'tech-block', 'tech block', 1, 0.88),
        ('A1', 'economy-block', 'economy block', 2, 0.95),
    ]


def test_generate_for_user_date_regenerates_unviewed_snapshot_with_latest_preference():
    snapshot_repository = StubSnapshotRepository()
    service, preference_repository, feed_service, _snapshot_repository, _read_repository = build_service(snapshot_repository=snapshot_repository)
    first = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='first-run')

    preference_repository.preference = build_preference(PreferenceMode.NARROW, ['economy'], ['macro'])
    feed_service.blocks = [
        {
            'key': 'economy-focus',
            'title': '깊게 보기',
            'weight': 1.0,
            'articles': [
                Article(
                    id='A1',
                    title='경제 뉴스',
                    summary='s',
                    content='c',
                    primary_category='economy',
                    subcategory='macro',
                    published_at='2026-05-20',
                    original_url='https://news.example/a1',
                    score_weight=0.95,
                )
            ],
        }
    ]

    regenerated = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='rerun')

    assert regenerated.id == first.id
    assert regenerated.preference_mode == PreferenceMode.NARROW
    assert regenerated.primary_categories == ['economy']
    assert regenerated.subcategories == ['macro']
    assert regenerated.generation_source == 'rerun'
    assert [item.article_id for item in regenerated.items] == ['A1']
    assert [item.block_key for item in regenerated.items] == ['economy-focus']


def test_generate_for_user_date_preserves_viewed_snapshot_when_preference_changes():
    snapshot_repository = StubSnapshotRepository()
    service, preference_repository, feed_service, _snapshot_repository, _read_repository = build_service(snapshot_repository=snapshot_repository)
    original = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='first-run')
    viewed_at = datetime(2026, 5, 20, 8, 0, tzinfo=UTC)
    snapshot_repository.mark_viewed(original.id, viewed_at)

    preference_repository.preference = build_preference(PreferenceMode.NARROW, ['economy'], ['macro'])
    feed_service.blocks = []

    preserved = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='rerun')

    assert preserved.id == original.id
    assert preserved.status == 'viewed'
    assert preserved.first_viewed_at == viewed_at
    assert preserved.preference_mode == PreferenceMode.WIDE
    assert preserved.primary_categories == ['tech', 'economy']
    assert preserved.generation_source == 'first-run'
    assert [item.article_id for item in preserved.items] == ['A2', 'A1']


def test_generate_for_user_date_replaces_viewed_snapshot_with_stale_article_ids():
    snapshot_repository = StubSnapshotRepository()
    service, _preference_repository, feed_service, _snapshot_repository, _read_repository = build_service(snapshot_repository=snapshot_repository)
    snapshot_repository.save(
        DailyFeedSnapshot(
            id=None,
            user_id='demo-user',
            feed_date='2026-05-20',
            status='viewed',
            generated_at=datetime(2026, 5, 20, 0, 0, tzinfo=UTC),
            first_viewed_at=datetime(2026, 5, 20, 8, 0, tzinfo=UTC),
            preference_mode=PreferenceMode.WIDE,
            primary_categories=['tech', 'economy'],
            subcategories=[],
            generation_source='legacy',
            items=[DailyFeedSnapshotItem(article_id='OLD', block_key='old', block_title='old', sort_order=1, score_weight=0.9)],
        )
    )

    regenerated = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='api:get_me_feed')

    assert regenerated.feed_date == '2026-05-20'
    assert regenerated.first_viewed_at is None
    assert regenerated.generation_source == 'api:get_me_feed'
    assert [item.article_id for item in regenerated.items] == ['A2', 'A1']
    assert feed_service.calls[-1] == (PreferenceMode.WIDE, ['tech', 'economy'], [], '2026-05-20')


def test_list_by_user_month_returns_only_persisted_snapshots_without_regenerating_from_current_preference():
    snapshot_repository = StubSnapshotRepository()
    service, preference_repository, feed_service, _snapshot_repository, _read_repository = build_service(snapshot_repository=snapshot_repository)
    may_snapshot = service.generate_for_user_date('demo-user', '2026-05-20', generation_source='first-run')
    other_month = service.generate_for_user_date('demo-user', '2026-04-30', generation_source='other-month')
    assert may_snapshot.id is not None
    assert other_month.id is not None
    snapshot_repository.mark_viewed(may_snapshot.id, datetime(2026, 5, 20, 8, 0, tzinfo=UTC))
    snapshot_repository.mark_viewed(other_month.id, datetime(2026, 4, 30, 8, 0, tzinfo=UTC))
    preference_repository.preference = build_preference(PreferenceMode.NARROW, ['economy'], ['macro'])
    feed_service.blocks = []

    snapshots = service.list_by_user_month('demo-user', '2026-05')

    assert [snapshot.feed_date for snapshot in snapshots] == ['2026-05-20']
    assert snapshots[0].preference_mode == PreferenceMode.WIDE
    assert [item.article_id for item in snapshots[0].items] == ['A2', 'A1']
    assert len(feed_service.calls) == 2


def test_get_by_user_date_returns_persisted_snapshot_and_none_for_missing_date():
    snapshot_repository = StubSnapshotRepository()
    service, _preference_repository, _feed_service, _snapshot_repository, _read_repository = build_service(snapshot_repository=snapshot_repository)
    snapshot = service.generate_for_user_date('demo-user', '2026-05-20')
    snapshot_repository.save(
        DailyFeedSnapshot(
            id=None,
            user_id='other-user',
            feed_date='2026-05-20',
            status='viewed',
            generated_at=datetime(2026, 5, 20, 0, 0, tzinfo=UTC),
            preference_mode=PreferenceMode.WIDE,
            primary_categories=['macro'],
            subcategories=[],
            generation_source='fixture',
            items=[DailyFeedSnapshotItem(article_id='OTHER', block_key='other', block_title='other', sort_order=1, score_weight=0.1)],
        )
    )

    found = service.get_by_user_date('demo-user', '2026-05-20')
    missing = service.get_by_user_date('demo-user', '2026-05-21')

    assert found is not None
    assert found.id == snapshot.id
    assert [item.article_id for item in found.items] == ['A2', 'A1']
    assert missing is None


def test_mark_viewed_and_mark_article_read_delegate_to_state_repositories():
    service, _preference_repository, _feed_service, _snapshot_repository, read_repository = build_service()
    snapshot = service.generate_for_user_date('demo-user', '2026-05-20')
    assert snapshot.id is not None
    viewed_at = datetime(2026, 5, 20, 8, 0, tzinfo=UTC)
    read_at = viewed_at + timedelta(minutes=5)

    viewed = service.mark_viewed(snapshot.id, viewed_at)
    service.mark_article_read('demo-user', 'A1', snapshot.id, read_at, read_source='detail')

    assert viewed.status == 'viewed'
    assert viewed.first_viewed_at == viewed_at
    assert read_repository.reads == [('demo-user', 'A1', snapshot.id, read_at, 'detail')]


def test_mark_article_read_completes_snapshot_when_all_items_are_read():
    service, _preference_repository, _feed_service, snapshot_repository, _read_repository = build_service()
    snapshot = service.generate_for_user_date('demo-user', '2026-05-20')
    assert snapshot.id is not None
    first_read_at = datetime(2026, 5, 20, 8, 5, tzinfo=UTC)
    second_read_at = first_read_at + timedelta(minutes=2)

    service.mark_article_read('demo-user', 'A1', snapshot.id, first_read_at, read_source='detail')
    after_first = snapshot_repository.get_by_user_date('demo-user', '2026-05-20')
    service.mark_article_read('demo-user', 'A2', snapshot.id, second_read_at, read_source='detail')
    completed = snapshot_repository.get_by_user_date('demo-user', '2026-05-20')

    assert after_first is not None
    assert after_first.status == 'generated'
    assert completed is not None
    assert completed.status == 'completed'
    assert completed.completed_at == second_read_at


def test_mark_article_read_without_snapshot_context_does_not_complete_any_snapshot():
    service, _preference_repository, _feed_service, snapshot_repository, read_repository = build_service()
    snapshot = service.generate_for_user_date('demo-user', '2026-05-20')
    read_at = datetime(2026, 5, 20, 8, 5, tzinfo=UTC)

    service.mark_article_read('demo-user', 'A1', None, read_at, read_source='detail')
    unchanged = snapshot_repository.get_by_user_date('demo-user', '2026-05-20')

    assert read_repository.reads == [('demo-user', 'A1', None, read_at, 'detail')]
    assert unchanged is not None
    assert unchanged.id == snapshot.id
    assert unchanged.status == 'generated'
    assert unchanged.completed_at is None
