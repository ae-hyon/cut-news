from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import PreferenceMode


class DomainModel(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


class Subcategory(DomainModel):
    id: int
    slug: str
    name: str
    description: str
    category_slug: str


class Category(DomainModel):
    id: int
    slug: str
    name: str
    description: str
    keywords: list[str] = Field(default_factory=list)
    subcategories: list[Subcategory] = Field(default_factory=list)


class Article(DomainModel):
    id: str
    title: str
    summary: str
    content: str
    primary_category: str
    subcategory: str
    published_at: str
    original_url: str
    score_weight: float = 1.0


class UserPreference(DomainModel):
    user_id: str
    mode: PreferenceMode
    primary_categories: list[str]
    subcategories: list[str]
    onboarding_completed: bool


class DailyFeedSnapshotItem(DomainModel):
    id: int | None = None
    snapshot_id: int | None = None
    article_id: str
    block_key: str
    block_title: str
    sort_order: int
    score_weight: float = 1.0


class DailyFeedSnapshot(DomainModel):
    id: int | None = None
    user_id: str
    feed_date: str
    status: str
    generated_at: datetime
    first_viewed_at: datetime | None = None
    completed_at: datetime | None = None
    preference_mode: PreferenceMode
    primary_categories: list[str]
    subcategories: list[str]
    generation_source: str | None = None
    items: list[DailyFeedSnapshotItem] = Field(default_factory=list)


class UserArticleRead(DomainModel):
    id: int | None = None
    user_id: str
    article_id: str
    snapshot_id: int | None = None
    opened_at: datetime
    read_at: datetime | None = None
    read_source: str | None = None


class ExternalIdentity(DomainModel):
    provider: str
    provider_subject: str
    user_id: str


class AuthSession(DomainModel):
    user_id: str | None
    session_state: str
    onboarding_completed: bool
    authenticated: bool
    auth_provider: str
    provider_subject: str | None = None
    preference: UserPreference | None = None


class RefreshSession(DomainModel):
    session_id: str
    user_id: str
    refresh_token_hash: str
    auth_provider: str
    provider_subject: str | None = None
    revoked: bool = False
    issued_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None


class AuthTokens(DomainModel):
    session: AuthSession
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    oauth_frontend_url: str | None = None


class Scrap(DomainModel):
    user_id: str
    article_id: str
