from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker

from app.domain.entities import Article, DailyFeedSnapshot, DailyFeedSnapshotItem, UserPreference
from app.domain.enums import PreferenceMode
from app.infrastructure.database import Base
from app.infrastructure.models import ArticleModel, UserArticleReadModel
from app.infrastructure.repositories import (
    SqlAlchemyDailyFeedSnapshotRepository,
    SqlAlchemyUserArticleReadRepository,
    SqlAlchemyUserPreferenceRepository,
)


def build_session():
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return session_local()


def seed_user_and_articles(db):
    preference_repository = SqlAlchemyUserPreferenceRepository(db)
    preference_repository.save(
        UserPreference(
            user_id='demo-user',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'tech'],
            subcategories=[],
            onboarding_completed=True,
        )
    )
    for article in [
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
    ]:
        db.add(ArticleModel(**article.model_dump()))
    db.commit()


def build_snapshot(feed_date: str = '2026-05-20') -> DailyFeedSnapshot:
    generated_at = datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    return DailyFeedSnapshot(
        user_id='demo-user',
        feed_date=feed_date,
        status='generated',
        generated_at=generated_at,
        preference_mode=PreferenceMode.WIDE,
        primary_categories=['economy', 'tech'],
        subcategories=[],
        generation_source='test-run',
        items=[
            DailyFeedSnapshotItem(article_id='A2', block_key='tech-block', block_title='tech block', sort_order=2, score_weight=0.88),
            DailyFeedSnapshotItem(article_id='A1', block_key='economy-block', block_title='economy block', sort_order=1, score_weight=0.95),
        ],
    )


def test_snapshot_save_and_get_by_user_date_preserves_preference_and_item_order():
    with build_session() as db:
        seed_user_and_articles(db)
        repository = SqlAlchemyDailyFeedSnapshotRepository(db)

        saved = repository.save(build_snapshot())
        loaded = repository.get_by_user_date('demo-user', '2026-05-20')

    assert saved.id is not None
    assert loaded is not None
    assert loaded.user_id == 'demo-user'
    assert loaded.feed_date == '2026-05-20'
    assert loaded.status == 'generated'
    assert loaded.generated_at == datetime(2026, 5, 20, 0, 30, tzinfo=UTC)
    assert loaded.preference_mode == PreferenceMode.WIDE
    assert loaded.primary_categories == ['economy', 'tech']
    assert loaded.subcategories == []
    assert loaded.generation_source == 'test-run'
    assert [item.article_id for item in loaded.items] == ['A1', 'A2']
    assert [item.sort_order for item in loaded.items] == [1, 2]


def test_snapshot_save_updates_same_user_date_and_replaces_items_idempotently():
    with build_session() as db:
        seed_user_and_articles(db)
        repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        first = repository.save(build_snapshot())

        updated = build_snapshot()
        updated.status = 'viewed'
        updated.primary_categories = ['tech']
        updated.items = [
            DailyFeedSnapshotItem(article_id='A2', block_key='tech-block', block_title='tech block', sort_order=1, score_weight=0.88),
        ]
        second = repository.save(updated)
        loaded = repository.get_by_user_date('demo-user', '2026-05-20')

    assert second.id == first.id
    assert loaded is not None
    assert loaded.status == 'viewed'
    assert loaded.primary_categories == ['tech']
    assert [item.article_id for item in loaded.items] == ['A2']


def test_list_by_user_month_returns_snapshots_for_requested_month_newest_first():
    with build_session() as db:
        seed_user_and_articles(db)
        repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        repository.save(build_snapshot('2026-05-19'))
        repository.save(build_snapshot('2026-05-21'))
        repository.save(build_snapshot('2026-04-30'))

        snapshots = repository.list_by_user_month('demo-user', '2026-05')

    assert [snapshot.feed_date for snapshot in snapshots] == ['2026-05-21', '2026-05-19']


def test_mark_viewed_sets_first_viewed_once_and_preserves_original_view_time():
    first_viewed_at = datetime(2026, 5, 20, 1, 0, tzinfo=UTC)
    later_viewed_at = first_viewed_at + timedelta(hours=1)
    with build_session() as db:
        seed_user_and_articles(db)
        repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        snapshot = repository.save(build_snapshot())

        viewed = repository.mark_viewed(snapshot.id, first_viewed_at)
        viewed_again = repository.mark_viewed(snapshot.id, later_viewed_at)

    assert viewed.first_viewed_at == first_viewed_at
    assert viewed.status == 'viewed'
    assert viewed_again.first_viewed_at == first_viewed_at
    assert viewed_again.status == 'viewed'


def test_user_article_read_repository_marks_reads_idempotently_for_snapshot():
    read_at = datetime(2026, 5, 20, 2, 0, tzinfo=UTC)
    later_read_at = read_at + timedelta(minutes=5)
    with build_session() as db:
        seed_user_and_articles(db)
        snapshot_repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        read_repository = SqlAlchemyUserArticleReadRepository(db)
        snapshot = snapshot_repository.save(build_snapshot())

        read_repository.mark_read('demo-user', 'A1', snapshot.id, read_at)
        read_repository.mark_read('demo-user', 'A1', snapshot.id, later_read_at)
        read_repository.mark_read('demo-user', 'A2', snapshot.id, later_read_at)
        read_ids = read_repository.list_read_article_ids('demo-user', snapshot.id)
        read_row_count = db.scalar(select(func.count()).select_from(UserArticleReadModel))

    assert read_ids == {'A1', 'A2'}
    assert read_row_count == 2
