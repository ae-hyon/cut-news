from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.application.auth.query_service import AuthQueryService
from app.application.auth.state_service import OAuthStateService
from app.application.auth.token_service import AuthTokenService
from app.application.services.auth_service import AuthService, DefaultKakaoOAuthClient
from app.application.services.catalog_service import CatalogService
from app.application.services.daily_feed_snapshot_service import DailyFeedSnapshotService
from app.application.services.feed_service import FeedService
from app.application.services.summary_service import SummaryGatewayService
from app.application.services.user_service import UserPreferenceService
from app.infrastructure.database import get_db
from app.infrastructure.repositories import (
    SqlAlchemyArticleRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyDailyFeedSnapshotRepository,
    SqlAlchemyExternalIdentityRepository,
    SqlAlchemyRefreshSessionRepository,
    SqlAlchemyScrapRepository,
    SqlAlchemyUserArticleReadRepository,
    SqlAlchemyUserPreferenceRepository,
)
from app.domain.entities import AuthSession
from app.common.config import settings


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(SqlAlchemyCategoryRepository(db))


def get_user_preference_service(db: Session = Depends(get_db)) -> UserPreferenceService:
    return UserPreferenceService(SqlAlchemyUserPreferenceRepository(db), SqlAlchemyCategoryRepository(db))


def get_feed_service(db: Session = Depends(get_db)) -> FeedService:
    return FeedService(SqlAlchemyArticleRepository(db), SqlAlchemyUserPreferenceRepository(db), SqlAlchemyScrapRepository(db))


def get_daily_feed_snapshot_service(db: Session = Depends(get_db)) -> DailyFeedSnapshotService:
    article_repository = SqlAlchemyArticleRepository(db)
    preference_repository = SqlAlchemyUserPreferenceRepository(db)
    scrap_repository = SqlAlchemyScrapRepository(db)
    return DailyFeedSnapshotService(
        feed_service=FeedService(article_repository, preference_repository, scrap_repository),
        preference_repository=preference_repository,
        snapshot_repository=SqlAlchemyDailyFeedSnapshotRepository(db),
        read_repository=SqlAlchemyUserArticleReadRepository(db),
    )


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    identity_repository = SqlAlchemyExternalIdentityRepository(db)
    preference_repository = SqlAlchemyUserPreferenceRepository(db)
    refresh_repository = SqlAlchemyRefreshSessionRepository(db)
    token_service = AuthTokenService(refresh_repository)
    return AuthService(
        oauth_client=DefaultKakaoOAuthClient(),
        identity_repository=identity_repository,
        preference_repository=preference_repository,
        refresh_session_repository=refresh_repository,
        state_service=OAuthStateService(),
        token_service=token_service,
        query_service=AuthQueryService(
            identity_repository=identity_repository,
            preference_repository=preference_repository,
            token_service=token_service,
        ),
    )


access_token_cookie = APIKeyCookie(
    name=settings.auth_access_cookie_name,
    scheme_name='AccessTokenCookie',
    auto_error=False,
    description='HttpOnly access-token cookie set by the Kakao callback or token refresh endpoint.',
)


def get_current_session(
    annoyingcap_access_token: str | None = Security(access_token_cookie),
    service: AuthService = Depends(get_auth_service),
) -> AuthSession:
    return service.resolve_session(access_token=annoyingcap_access_token)


def require_current_user(session: AuthSession = Depends(get_current_session)) -> AuthSession:
    if not session.user_id or not session.authenticated:
        raise HTTPException(status_code=401, detail='Authentication required')
    return session


def get_summary_gateway_service() -> SummaryGatewayService:
    return SummaryGatewayService()
