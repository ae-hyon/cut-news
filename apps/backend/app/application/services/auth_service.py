from __future__ import annotations

from app.application.auth.errors import AuthError
from app.application.auth.kakao_oauth_service import DefaultKakaoOAuthClient, KakaoOAuthClient
from app.application.auth.query_service import AuthQueryService
from app.application.auth.state_service import OAuthStateService
from app.application.auth.token_service import AuthTokenService, build_internal_user_id
from app.domain.entities import AuthSession, AuthTokens, ExternalIdentity
from app.domain.repositories import ExternalIdentityRepository, RefreshSessionRepository, UserPreferenceRepository


class AuthService:
    def __init__(
        self,
        oauth_client: KakaoOAuthClient,
        identity_repository: ExternalIdentityRepository,
        preference_repository: UserPreferenceRepository,
        refresh_session_repository: RefreshSessionRepository,
        state_service: OAuthStateService | None = None,
        token_service: AuthTokenService | None = None,
        query_service: AuthQueryService | None = None,
    ):
        self.oauth_client = oauth_client
        self.identity_repository = identity_repository
        self.preference_repository = preference_repository
        self.refresh_session_repository = refresh_session_repository
        self.state_service = state_service or OAuthStateService()
        self.token_service = token_service or AuthTokenService(refresh_session_repository)
        self.query_service = query_service or AuthQueryService(
            identity_repository=identity_repository,
            preference_repository=preference_repository,
            token_service=self.token_service,
        )

    def start_kakao_auth(self) -> dict:
        state = self.state_service.issue()
        return {
            'provider': 'kakao',
            'state': state,
            'authorization_url': self.oauth_client.build_authorization_url(state),
        }

    def complete_kakao_callback(self, code: str, state: str) -> AuthTokens:
        self.state_service.verify(state)
        identity = self.oauth_client.exchange_code_for_identity(code, state)
        existing = self.identity_repository.get_by_provider_subject(identity.provider, identity.provider_subject)
        if existing:
            user_id = existing.user_id
        else:
            user_id = build_internal_user_id(identity.provider, identity.provider_subject)
            self.query_service.ensure_preference_exists(user_id)
            self.identity_repository.save(
                ExternalIdentity(provider=identity.provider, provider_subject=identity.provider_subject, user_id=user_id)
            )
        preference = self.query_service.ensure_preference_exists(user_id)
        return self.token_service.issue_tokens(user_id, identity.provider, identity.provider_subject, preference.onboarding_completed)

    def issue_tokens(self, user_id: str, auth_provider: str, provider_subject: str | None, onboarding_completed: bool):
        return self.token_service.issue_tokens(user_id, auth_provider, provider_subject, onboarding_completed)

    def refresh_session(self, refresh_token: str) -> AuthTokens:
        saved = self.token_service.get_refresh_session(refresh_token)
        if not saved or saved.revoked:
            raise AuthError('invalid_refresh_token', 'Refresh token is invalid or expired.', status_code=401)
        self.token_service.revoke_refresh_token(refresh_token)
        preference = self.query_service.ensure_preference_exists(saved.user_id)
        return self.token_service.issue_tokens(saved.user_id, saved.auth_provider, saved.provider_subject, preference.onboarding_completed)

    def logout(self, refresh_token: str | None) -> None:
        if refresh_token:
            self.token_service.revoke_refresh_token(refresh_token)

    def resolve_session(
        self,
        user_id: str | None = None,
        provider: str | None = None,
        provider_subject: str | None = None,
        access_token: str | None = None,
    ) -> AuthSession:
        return self.query_service.resolve_session(
            user_id=user_id,
            provider=provider,
            provider_subject=provider_subject,
            access_token=access_token,
        )


__all__ = ['AuthError', 'AuthService', 'DefaultKakaoOAuthClient', 'KakaoOAuthClient']
