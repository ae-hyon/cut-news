from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.common.config import settings
from app.domain.entities import AuthSession, AuthTokens, RefreshSession, UserPreference
from app.domain.enums import PreferenceMode
from app.domain.repositories import RefreshSessionRepository

DEFAULT_PRIMARY = ['sectors', 'macro', 'assets', 'policy']


class AuthTokenService:
    def __init__(self, refresh_session_repository: RefreshSessionRepository):
        self.refresh_session_repository = refresh_session_repository

    @staticmethod
    def hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode('utf-8')).hexdigest()

    def issue_tokens(
        self,
        user_id: str,
        auth_provider: str,
        provider_subject: str | None,
        onboarding_completed: bool,
        preference: UserPreference | None = None,
    ) -> AuthTokens:
        session_state = 'onboarded' if onboarding_completed else 'authenticated'
        session = AuthSession(
            user_id=user_id,
            session_state=session_state,
            onboarding_completed=onboarding_completed,
            authenticated=True,
            auth_provider=auth_provider,
            provider_subject=provider_subject,
            preference=preference,
        )
        access_token = self.encode_access_token(session)
        refresh_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        refresh_session = RefreshSession(
            session_id=secrets.token_urlsafe(24),
            user_id=user_id,
            refresh_token_hash=self.hash_refresh_token(refresh_token),
            auth_provider=auth_provider,
            provider_subject=provider_subject,
            revoked=False,
            issued_at=now,
            last_used_at=now,
            revoked_at=None,
        )
        self.refresh_session_repository.save(refresh_session)
        return AuthTokens(session=session, access_token=access_token, refresh_token=refresh_token)

    def encode_access_token(self, session: AuthSession) -> str:
        now = datetime.now(UTC)
        payload = {
            'sub': session.user_id,
            'session_state': session.session_state,
            'onboarding_completed': session.onboarding_completed,
            'authenticated': session.authenticated,
            'auth_provider': session.auth_provider,
            'provider_subject': session.provider_subject,
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=settings.jwt_access_token_minutes)).timestamp()),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_access_token(self, access_token: str) -> AuthSession | None:
        try:
            payload = jwt.decode(access_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except jwt.PyJWTError:
            return None
        return AuthSession(
            user_id=payload.get('sub'),
            session_state='onboarded' if payload.get('onboarding_completed') else 'authenticated',
            onboarding_completed=bool(payload.get('onboarding_completed', False)),
            authenticated=True,
            auth_provider=payload.get('auth_provider', 'kakao'),
            provider_subject=payload.get('provider_subject'),
        )

    def get_refresh_session(self, refresh_token: str) -> RefreshSession | None:
        return self.refresh_session_repository.get_by_token_hash(self.hash_refresh_token(refresh_token))

    def revoke_refresh_token(self, refresh_token: str) -> None:
        self.refresh_session_repository.revoke_by_token_hash(self.hash_refresh_token(refresh_token))


def build_internal_user_id(provider: str, provider_subject: str) -> str:
    normalized = re.sub(r'[^a-zA-Z0-9_-]+', '-', provider_subject).strip('-') or 'user'
    if normalized.startswith(f'{provider}-'):
        return f'user-{normalized}'
    return f'user-{provider}-{normalized}'


def build_default_preference(user_id: str) -> UserPreference:
    return UserPreference(
        user_id=user_id,
        mode=PreferenceMode.WIDE,
        primary_categories=DEFAULT_PRIMARY.copy(),
        subcategories=[],
        onboarding_completed=False,
    )
