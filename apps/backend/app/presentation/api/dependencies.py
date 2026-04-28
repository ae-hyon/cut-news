from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.auth.query_service import AuthQueryService
from app.application.auth.state_service import OAuthStateService
from app.application.auth.token_service import AuthTokenService
from app.application.services.auth_service import AuthService, DefaultKakaoOAuthClient
from app.application.services.catalog_service import CatalogService
from app.application.services.feed_service import FeedService
from app.application.services.summary_service import SummaryGatewayService
from app.application.services.user_service import UserPreferenceService
from app.infrastructure.database import get_db
from app.infrastructure.repositories import (
    SqlAlchemyArticleRepository,
    SqlAlchemyCategoryRepository,
    SqlAlchemyExternalIdentityRepository,
    SqlAlchemyRefreshSessionRepository,
    SqlAlchemyScrapRepository,
    SqlAlchemyUserPreferenceRepository,
)


def get_catalog_service(db: Session = Depends(get_db)) -> CatalogService:
    return CatalogService(SqlAlchemyCategoryRepository(db))


def get_user_preference_service(db: Session = Depends(get_db)) -> UserPreferenceService:
    return UserPreferenceService(SqlAlchemyUserPreferenceRepository(db), SqlAlchemyCategoryRepository(db))


def get_feed_service(db: Session = Depends(get_db)) -> FeedService:
    return FeedService(SqlAlchemyArticleRepository(db), SqlAlchemyUserPreferenceRepository(db), SqlAlchemyScrapRepository(db))


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


def get_summary_gateway_service() -> SummaryGatewayService:
    return SummaryGatewayService()
