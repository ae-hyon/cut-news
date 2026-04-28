from __future__ import annotations

from app.domain.entities import AuthSession
from app.domain.repositories import ExternalIdentityRepository, UserPreferenceRepository

from app.application.auth.token_service import AuthTokenService, build_default_preference


class AuthQueryService:
    def __init__(
        self,
        identity_repository: ExternalIdentityRepository,
        preference_repository: UserPreferenceRepository,
        token_service: AuthTokenService,
    ):
        self.identity_repository = identity_repository
        self.preference_repository = preference_repository
        self.token_service = token_service

    def resolve_session(
        self,
        user_id: str | None = None,
        provider: str | None = None,
        provider_subject: str | None = None,
        access_token: str | None = None,
    ) -> AuthSession:
        if access_token:
            decoded = self.token_service.decode_access_token(access_token)
            if decoded:
                return decoded
        if provider == 'kakao' and provider_subject:
            identity = self.identity_repository.get_by_provider_subject(provider, provider_subject)
            if not identity:
                return self.anonymous_session()
            preference = self.ensure_preference_exists(identity.user_id)
            return AuthSession(
                user_id=identity.user_id,
                session_state='onboarded' if preference.onboarding_completed else 'authenticated',
                onboarding_completed=preference.onboarding_completed,
                authenticated=True,
                auth_provider=provider,
                provider_subject=provider_subject,
            )
        if user_id:
            preference = self.ensure_preference_exists(user_id)
            return AuthSession(
                user_id=preference.user_id,
                session_state='onboarded' if preference.onboarding_completed else 'anonymous',
                onboarding_completed=preference.onboarding_completed,
                authenticated=False,
                auth_provider='demo' if preference.onboarding_completed else 'none',
                provider_subject=None,
            )
        return self.anonymous_session()

    def ensure_preference_exists(self, user_id: str):
        existing = self.preference_repository.get(user_id)
        if existing:
            return existing
        return self.preference_repository.save(build_default_preference(user_id))

    @staticmethod
    def anonymous_session() -> AuthSession:
        return AuthSession(
            user_id=None,
            session_state='anonymous',
            onboarding_completed=False,
            authenticated=False,
            auth_provider='none',
            provider_subject=None,
        )
