from __future__ import annotations

import hashlib

from app.application.services.auth_service import AuthError, AuthService
from app.domain.entities import ExternalIdentity, RefreshSession, UserPreference
from app.domain.enums import PreferenceMode


class StubKakaoOAuthClient:
    def build_authorization_url(self, state: str) -> str:
        return f'https://kauth.kakao.com/oauth/authorize?state={state}'

    def exchange_code_for_identity(self, code: str, state: str) -> ExternalIdentity:
        assert code == 'issued-code'
        assert '.' in state
        return ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='')


class StubExternalIdentityRepository:
    def __init__(self, existing: ExternalIdentity | None = None):
        self.existing = existing
        self.saved: ExternalIdentity | None = None

    def get_by_provider_subject(self, provider: str, provider_subject: str) -> ExternalIdentity | None:
        if self.saved and self.saved.provider == provider and self.saved.provider_subject == provider_subject:
            return self.saved
        if self.existing and self.existing.provider == provider and self.existing.provider_subject == provider_subject:
            return self.existing
        return None

    def save(self, identity: ExternalIdentity) -> ExternalIdentity:
        self.saved = identity
        return identity


class StubUserPreferenceRepository:
    def __init__(self, existing: UserPreference | None = None):
        self.existing = existing
        self.saved: UserPreference | None = None

    def get(self, user_id: str) -> UserPreference | None:
        if self.saved and self.saved.user_id == user_id:
            return self.saved
        if self.existing and self.existing.user_id == user_id:
            return self.existing
        return None

    def save(self, preference: UserPreference) -> UserPreference:
        self.saved = preference
        return preference


class StubRefreshSessionRepository:
    def __init__(self, existing: RefreshSession | None = None):
        self.existing = existing
        self.saved: RefreshSession | None = None
        self.revoked_tokens: list[str] = []

    @staticmethod
    def _hash(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()

    def get_by_token_hash(self, refresh_token_hash: str) -> RefreshSession | None:
        if self.saved and self.saved.refresh_token_hash == refresh_token_hash:
            return self.saved
        if self.existing and self.existing.refresh_token_hash == refresh_token_hash:
            return self.existing
        return None

    def save(self, session: RefreshSession) -> RefreshSession:
        self.saved = session
        return session

    def revoke_by_token_hash(self, refresh_token_hash: str) -> None:
        self.revoked_tokens.append(refresh_token_hash)
        if self.saved and self.saved.refresh_token_hash == refresh_token_hash:
            self.saved = self.saved.model_copy(update={'revoked': True})
        if self.existing and self.existing.refresh_token_hash == refresh_token_hash:
            self.existing = self.existing.model_copy(update={'revoked': True})


def test_complete_kakao_callback_creates_mapping_and_default_preference_for_new_user():
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=StubRefreshSessionRepository(),
    )
    issued = service.start_kakao_auth()

    result = service.complete_kakao_callback(code='issued-code', state=issued['state'])

    assert result.session.user_id == 'user-kakao-123'
    assert result.session.session_state == 'authenticated'
    assert result.session.onboarding_completed is False
    assert result.session.authenticated is True
    assert result.session.auth_provider == 'kakao'
    assert result.session.provider_subject == 'kakao-123'
    assert result.access_token
    assert result.refresh_token
    assert service.refresh_session_repository.saved is not None
    assert service.refresh_session_repository.saved.refresh_token_hash != result.refresh_token
    assert 'user-kakao-123' not in service.refresh_session_repository.saved.refresh_token_hash


def test_resolve_session_returns_onboarded_state_for_existing_kakao_identity_after_preferences_complete():
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='demo-user')
        ),
        preference_repository=StubUserPreferenceRepository(
            existing=UserPreference(
                user_id='demo-user',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=True,
            )
        ),
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    session = service.resolve_session(provider='kakao', provider_subject='kakao-123')

    assert session.user_id == 'demo-user'
    assert session.session_state == 'onboarded'
    assert session.onboarding_completed is True
    assert session.authenticated is True
    assert session.auth_provider == 'kakao'
    assert session.provider_subject == 'kakao-123'


def test_refresh_session_rotates_refresh_token_and_preserves_authenticated_session():
    refresh_repo = StubRefreshSessionRepository(
        existing=RefreshSession(
            session_id='session-1',
            user_id='demo-user',
            refresh_token_hash=hashlib.sha256('refresh-old'.encode('utf-8')).hexdigest(),
            auth_provider='kakao',
            provider_subject='kakao-123',
            revoked=False,
        )
    )
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='demo-user')
        ),
        preference_repository=StubUserPreferenceRepository(
            existing=UserPreference(
                user_id='demo-user',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=True,
            )
        ),
        refresh_session_repository=refresh_repo,
    )

    result = service.refresh_session('refresh-old')

    assert result.session.user_id == 'demo-user'
    assert result.session.authenticated is True
    assert result.refresh_token != 'refresh-old'
    assert AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=refresh_repo,
    ).token_service.hash_refresh_token('refresh-old') in refresh_repo.revoked_tokens


def test_resolve_session_accepts_access_token():
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='demo-user')
        ),
        preference_repository=StubUserPreferenceRepository(
            existing=UserPreference(
                user_id='demo-user',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=True,
            )
        ),
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    issued = service.issue_tokens('demo-user', 'kakao', 'kakao-123', onboarding_completed=True)
    session = service.resolve_session(access_token=issued.access_token)

    assert session.user_id == 'demo-user'
    assert session.authenticated is True
    assert session.auth_provider == 'kakao'


def test_logout_revokes_refresh_token():
    refresh_repo = StubRefreshSessionRepository(
        existing=RefreshSession(
            session_id='session-1',
            user_id='demo-user',
            refresh_token_hash=hashlib.sha256('refresh-old'.encode('utf-8')).hexdigest(),
            auth_provider='kakao',
            provider_subject='kakao-123',
            revoked=False,
        )
    )
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=refresh_repo,
    )

    service.logout('refresh-old')

    assert service.token_service.hash_refresh_token('refresh-old') in refresh_repo.revoked_tokens


def test_start_kakao_auth_returns_signed_state_token_not_raw_nonce():
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    result = service.start_kakao_auth()

    assert result['state']
    assert '.' in result['state']
    assert result['authorization_url'].endswith(result['state'])


def test_complete_kakao_callback_rejects_tampered_state_before_code_exchange():
    class ExplodingOAuthClient(StubKakaoOAuthClient):
        def exchange_code_for_identity(self, code: str, state: str) -> ExternalIdentity:
            raise AssertionError('should not exchange code when state is invalid')

    service = AuthService(
        oauth_client=ExplodingOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    try:
        service.complete_kakao_callback(code='issued-code', state='tampered-state')
    except AuthError as exc:
        assert exc.code == 'invalid_oauth_state'
        assert exc.status_code == 401
    else:
        raise AssertionError('expected AuthError for invalid state')


def test_complete_kakao_callback_maps_kakao_exchange_failure_to_bad_gateway_auth_error():
    class FailingOAuthClient(StubKakaoOAuthClient):
        def exchange_code_for_identity(self, code: str, state: str) -> ExternalIdentity:
            raise AuthError('kakao_token_exchange_failed', 'Kakao token exchange failed.', status_code=502)

    service = AuthService(
        oauth_client=FailingOAuthClient(),
        identity_repository=StubExternalIdentityRepository(),
        preference_repository=StubUserPreferenceRepository(),
        refresh_session_repository=StubRefreshSessionRepository(),
    )
    issued = service.start_kakao_auth()

    try:
        service.complete_kakao_callback(code='issued-code', state=issued['state'])
    except AuthError as exc:
        assert exc.code == 'kakao_token_exchange_failed'
        assert exc.status_code == 502
    else:
        raise AssertionError('expected AuthError for Kakao exchange failure')


def test_resolve_session_keeps_authenticated_state_for_kakao_user_before_onboarding_complete():
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='user-kakao-123')
        ),
        preference_repository=StubUserPreferenceRepository(
            existing=UserPreference(
                user_id='user-kakao-123',
                mode=PreferenceMode.WIDE,
                primary_categories=['economy', 'politics', 'tech'],
                subcategories=[],
                onboarding_completed=False,
            )
        ),
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    session = service.resolve_session(provider='kakao', provider_subject='kakao-123')

    assert session.session_state == 'authenticated'
    assert session.authenticated is True
    assert session.onboarding_completed is False


def test_resolve_session_returns_onboarded_for_authenticated_kakao_user_after_preferences_complete():
    preference_repo = StubUserPreferenceRepository(
        existing=UserPreference(
            user_id='user-kakao-123',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=False,
        )
    )
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='user-kakao-123')
        ),
        preference_repository=preference_repo,
        refresh_session_repository=StubRefreshSessionRepository(),
    )

    preference_repo.save(
        UserPreference(
            user_id='user-kakao-123',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=True,
        )
    )

    session = service.resolve_session(provider='kakao', provider_subject='kakao-123')

    assert session.session_state == 'onboarded'
    assert session.authenticated is True
    assert session.onboarding_completed is True



def test_resolve_session_refreshes_onboarding_state_for_stale_access_token():
    preference_repo = StubUserPreferenceRepository(
        existing=UserPreference(
            user_id='user-kakao-123',
            mode=PreferenceMode.WIDE,
            primary_categories=['economy', 'politics', 'tech'],
            subcategories=[],
            onboarding_completed=True,
        )
    )
    service = AuthService(
        oauth_client=StubKakaoOAuthClient(),
        identity_repository=StubExternalIdentityRepository(
            existing=ExternalIdentity(provider='kakao', provider_subject='kakao-123', user_id='user-kakao-123')
        ),
        preference_repository=preference_repo,
        refresh_session_repository=StubRefreshSessionRepository(),
    )
    issued = service.issue_tokens('user-kakao-123', 'kakao', 'kakao-123', onboarding_completed=False)

    session = service.resolve_session(access_token=issued.access_token)

    assert session.user_id == 'user-kakao-123'
    assert session.session_state == 'onboarded'
    assert session.onboarding_completed is True
    assert session.authenticated is True
