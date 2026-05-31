from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.entities import AuthSession, DailyFeedSnapshot, UserPreference
from app.domain.enums import PreferenceMode
from app.domain.exceptions import ValidationError
from app.presentation.api.dependencies import (
    get_current_session,
    get_daily_feed_snapshot_service,
    get_feed_service,
    get_user_preference_service,
)
from app.presentation.api.routes import users
from app.presentation.api.routes.users import router


CURRENT_SESSION = AuthSession(
    user_id='user-kakao-123',
    session_state='authenticated',
    onboarding_completed=False,
    authenticated=True,
    auth_provider='kakao',
    provider_subject='kakao-123',
)


class StubUserPreferenceService:
    def get_preferences(self, user_id: str) -> UserPreference:
        assert user_id == 'user-kakao-123'
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=False,
        )

    def update_preferences(self, user_id: str, mode: str, primary_categories: list[str], subcategories: list[str]) -> UserPreference:
        assert user_id == 'user-kakao-123'
        if mode == 'wide' and subcategories:
            raise ValidationError('wide mode does not accept subcategories')
        return UserPreference(
            user_id=user_id,
            mode=PreferenceMode(mode),
            primary_categories=primary_categories,
            subcategories=subcategories,
            onboarding_completed=True,
        )


def build_client(
    session: AuthSession = CURRENT_SESSION,
    *,
    feed_service=None,
    snapshot_service=None,
) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix='/v1')
    app.dependency_overrides[get_user_preference_service] = lambda: StubUserPreferenceService()
    app.dependency_overrides[get_current_session] = lambda: session
    if feed_service is not None:
        app.dependency_overrides[get_feed_service] = lambda: feed_service
    if snapshot_service is not None:
        app.dependency_overrides[get_daily_feed_snapshot_service] = lambda: snapshot_service
    return TestClient(app)


def test_get_me_preference_returns_current_users_preference():
    client = build_client()

    response = client.get('/v1/me/preference')

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'user-kakao-123',
        'mode': 'wide',
        'primary_categories': ['economy', 'politics', 'tech'],
        'subcategories': [],
        'onboarding_completed': False,
    }


def test_put_me_preference_returns_422_for_invalid_onboarding_payload():
    client = build_client()

    response = client.put(
        '/v1/me/preference',
        json={
            'mode': 'wide',
            'primary_categories': ['economy', 'politics', 'tech'],
            'subcategories': ['macro'],
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'] == 'wide mode does not accept subcategories'


def test_put_me_preference_marks_onboarding_completed_when_valid():
    client = build_client()

    response = client.put(
        '/v1/me/preference',
        json={
            'mode': 'narrow',
            'primary_categories': ['economy'],
            'subcategories': ['macro', 'real-estate'],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['user_id'] == 'user-kakao-123'
    assert body['mode'] == 'narrow'
    assert body['onboarding_completed'] is True
    assert body['subcategories'] == ['macro', 'real-estate']


def test_patch_me_preference_updates_current_users_interest_categories():
    client = build_client()

    response = client.patch(
        '/v1/me/preference',
        json={
            'mode': 'wide',
            'primary_categories': ['economy', 'politics', 'tech'],
            'subcategories': [],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        'user_id': 'user-kakao-123',
        'mode': 'wide',
        'primary_categories': ['economy', 'politics', 'tech'],
        'subcategories': [],
        'onboarding_completed': True,
    }


def test_me_preference_requires_authenticated_user():
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

    response = client.get('/v1/me/preference')

    assert response.status_code == 401
    assert response.json()['detail'] == 'Authentication required'


def kst_at(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo('Asia/Seoul'))


def test_home_feed_window_publishes_previous_feed_until_025959():
    window = users.resolve_home_feed_window(kst_at('2026-06-01T02:59:59'))

    assert window.publication_status == 'published'
    assert window.feed_date == '2026-05-31'
    assert window.next_publish_at == '2026-06-01T09:00:00+09:00'


def test_home_feed_window_blocks_today_between_030000_and_085959():
    at_start = users.resolve_home_feed_window(kst_at('2026-05-31T03:00:00'))
    at_end = users.resolve_home_feed_window(kst_at('2026-05-31T08:59:59'))

    assert at_start.publication_status == 'before_publication'
    assert at_start.feed_date == '2026-05-31'
    assert at_start.next_publish_at == '2026-05-31T09:00:00+09:00'
    assert at_end.publication_status == 'before_publication'
    assert at_end.feed_date == '2026-05-31'
    assert at_end.next_publish_at == '2026-05-31T09:00:00+09:00'


def test_home_feed_window_publishes_today_from_090000():
    window = users.resolve_home_feed_window(kst_at('2026-05-31T09:00:00'))

    assert window.publication_status == 'published'
    assert window.feed_date == '2026-05-31'
    assert window.next_publish_at == '2026-06-01T09:00:00+09:00'


class FixedDateTime(datetime):
    fixed_now: datetime

    @classmethod
    def now(cls, tz=None):
        return cls.fixed_now.astimezone(tz) if tz is not None else cls.fixed_now


class StubFeedService:
    def list_scraps(self, user_id: str):
        assert user_id == 'user-kakao-123'
        return []


class RecordingSnapshotService:
    def __init__(self):
        self.generated_feed_dates: list[str] = []
        self.marked_snapshot_ids: list[int] = []

    def generate_for_user_date(self, user_id: str, feed_date: str, generation_source: str):
        assert user_id == 'user-kakao-123'
        assert generation_source == 'api:get_me_feed'
        self.generated_feed_dates.append(feed_date)
        return DailyFeedSnapshot(
            id=42,
            user_id=user_id,
            feed_date=feed_date,
            status='generated',
            generated_at=datetime(2026, 5, 31, 0, 0, tzinfo=ZoneInfo('UTC')),
            preference_mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            items=[],
        )

    def mark_viewed(self, snapshot_id: int):
        self.marked_snapshot_ids.append(snapshot_id)
        return DailyFeedSnapshot(
            id=snapshot_id,
            user_id='user-kakao-123',
            feed_date=self.generated_feed_dates[-1],
            status='viewed',
            generated_at=datetime(2026, 5, 31, 0, 0, tzinfo=ZoneInfo('UTC')),
            preference_mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            items=[],
        )

    def list_read_article_ids(self, user_id: str, snapshot_id: int):
        return set()


class FailingSnapshotService:
    called = False

    def generate_for_user_date(self, *args, **kwargs):
        self.called = True
        raise AssertionError('snapshot generation must not run before publication')


def test_get_me_feed_returns_425_before_publication(monkeypatch):
    FixedDateTime.fixed_now = kst_at('2026-05-31T03:00:00')
    monkeypatch.setattr(users, 'datetime', FixedDateTime)
    snapshot_service = FailingSnapshotService()
    client = build_client(feed_service=StubFeedService(), snapshot_service=snapshot_service)

    response = client.get('/v1/me/feed')

    assert response.status_code == 425
    assert response.json()['detail'] == {
        'publication_status': 'before_publication',
        'feed_date': '2026-05-31',
        'next_publish_at': '2026-05-31T09:00:00+09:00',
    }
    assert snapshot_service.called is False


def test_get_me_feed_uses_previous_feed_date_until_025959(monkeypatch):
    FixedDateTime.fixed_now = kst_at('2026-06-01T02:59:59')
    monkeypatch.setattr(users, 'datetime', FixedDateTime)
    snapshot_service = RecordingSnapshotService()
    client = build_client(feed_service=StubFeedService(), snapshot_service=snapshot_service)

    response = client.get('/v1/me/feed')

    assert response.status_code == 200
    assert response.json()['feed_date'] == '2026-05-31'
    assert snapshot_service.generated_feed_dates == ['2026-05-31']
    assert snapshot_service.marked_snapshot_ids == [42]
