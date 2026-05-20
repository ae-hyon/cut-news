from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.domain.entities import Article, AuthSession, DailyFeedSnapshot, DailyFeedSnapshotItem
from app.domain.enums import PreferenceMode
from app.presentation.api.dependencies import get_current_session, get_daily_feed_snapshot_service, get_feed_service
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
    def get_article(self, article_id: str):
        articles = {
            'A1': Article(id='A1', title='t1', summary='s', content='c', primary_category='tech', subcategory='ai', published_at='2026-04-15', original_url='https://t/1', score_weight=0.88),
            'A2': Article(id='A2', title='t2', summary='s2', content='c2', primary_category='macro', subcategory='rates-fx', published_at='2026-04-15', original_url='https://t/2', score_weight=0.77),
        }
        return articles[article_id]

    def list_scraps(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return [self.get_article('A1')]

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


class StubDailyFeedSnapshotService:
    def __init__(self):
        self.generated_for: tuple[str, str, str] | None = None
        self.marked_viewed_id: int | None = None
        self.archive_snapshot = DailyFeedSnapshot(
            id=42,
            user_id='user-kakao-123',
            feed_date='2026-04-15',
            status='viewed',
            generated_at=datetime(2026, 4, 15, 0, 0, tzinfo=UTC),
            first_viewed_at=datetime(2026, 4, 15, 1, 2, tzinfo=UTC),
            preference_mode=PreferenceMode.WIDE,
            primary_categories=['tech', 'macro'],
            subcategories=[],
            generation_source='test',
            items=[
                DailyFeedSnapshotItem(snapshot_id=42, article_id='A2', block_key='macro-block', block_title='macro block', sort_order=1, score_weight=0.77),
                DailyFeedSnapshotItem(snapshot_id=42, article_id='A1', block_key='tech-block', block_title='tech block', sort_order=2, score_weight=0.88),
            ],
        )

    def generate_for_user_date(self, user_id: str, feed_date: str, generation_source: str | None = None):
        self.generated_for = (user_id, feed_date, generation_source or '')
        return self.archive_snapshot.model_copy(
            update={
                'user_id': user_id,
                'feed_date': feed_date,
                'status': 'generated',
                'first_viewed_at': None,
                'generation_source': generation_source,
            },
            deep=True,
        )

    def list_by_user_month(self, user_id: str, month: str):
        assert user_id == 'user-kakao-123'
        assert month == '2026-04'
        return [self.archive_snapshot.model_copy(deep=True)]

    def get_by_user_date(self, user_id: str, feed_date: str):
        assert user_id == 'user-kakao-123'
        if feed_date == '2026-04-15':
            return self.archive_snapshot.model_copy(deep=True)
        return None

    def mark_viewed(self, snapshot_id: int):
        self.marked_viewed_id = snapshot_id
        if snapshot_id == 42 and self.generated_for is None:
            return self.archive_snapshot.model_copy(deep=True)
        user_id, feed_date, generation_source = self.generated_for or ('user-kakao-123', datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat(), 'api:get_me_feed')
        snapshot = self.generate_for_user_date(user_id, feed_date, generation_source)
        return snapshot.model_copy(update={'status': 'viewed', 'first_viewed_at': datetime(2026, 5, 20, 1, 2, tzinfo=UTC)})

    def list_read_article_ids(self, user_id: str, snapshot_id: int):
        assert user_id == 'user-kakao-123'
        assert snapshot_id == 42
        return {'A2'}


def build_client(session: AuthSession = CURRENT_SESSION, snapshot_service: StubDailyFeedSnapshotService | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_feed_service] = lambda: StubFeedService()
    app.dependency_overrides[get_daily_feed_snapshot_service] = lambda: snapshot_service or StubDailyFeedSnapshotService()
    app.dependency_overrides[get_current_session] = lambda: session
    return TestClient(app)


def test_me_feed_returns_current_users_snapshot_feed():
    today = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    snapshot_service = StubDailyFeedSnapshotService()
    client = build_client(snapshot_service=snapshot_service)

    response = client.get('/v1/me/feed')

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['snapshot_id'] == 42
    assert body['feed_date'] == today
    assert body['status'] == 'viewed'
    assert body['read_count'] == 1
    assert body['total_count'] == 2
    assert body['mode'] == 'wide'
    assert body['blocks'][0]['key'] == 'macro-block'
    assert body['blocks'][0]['articles'][0]['id'] == 'A2'
    assert body['blocks'][1]['key'] == 'tech-block'
    assert body['blocks'][1]['articles'][0]['id'] == 'A1'
    assert body['blocks'][1]['articles'][0]['is_scrapped'] is True
    assert snapshot_service.generated_for == ('user-kakao-123', today, 'api:get_me_feed')
    assert snapshot_service.marked_viewed_id == 42


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


def test_me_archive_month_returns_snapshot_days_without_runtime_items():
    snapshot_service = StubDailyFeedSnapshotService()
    client = build_client(snapshot_service=snapshot_service)

    response = client.get('/v1/me/archive?month=2026-04')

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['month'] == '2026-04'
    assert body['days'] == [
        {
            'date': '2026-04-15',
            'snapshot_id': 42,
            'status': 'viewed',
            'has_feed': True,
            'count': 2,
            'total_count': 2,
            'read_count': 1,
            'first_viewed_at': '2026-04-15T01:02:00Z',
            'completed_at': None,
        }
    ]


def test_me_archive_date_returns_snapshot_items_and_marks_viewed():
    snapshot_service = StubDailyFeedSnapshotService()
    client = build_client(snapshot_service=snapshot_service)

    response = client.get('/v1/me/archive/2026-04-15')

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['date'] == '2026-04-15'
    assert body['snapshot_id'] == 42
    assert body['status'] == 'viewed'
    assert body['read_count'] == 1
    assert body['total_count'] == 2
    assert body['items'][0]['id'] == 'A2'
    assert body['items'][0]['is_scrapped'] is False
    assert body['items'][1]['id'] == 'A1'
    assert body['items'][1]['is_scrapped'] is True
    assert snapshot_service.marked_viewed_id == 42


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
