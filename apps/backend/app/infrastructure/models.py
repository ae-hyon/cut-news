from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class CategoryModel(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255), default='')
    keywords_json: Mapped[str] = mapped_column(Text, default='[]')

    subcategories: Mapped[list['SubcategoryModel']] = relationship(back_populates='category', cascade='all, delete-orphan')


class SubcategoryModel(Base):
    __tablename__ = 'subcategories'
    __table_args__ = (UniqueConstraint('category_id', 'slug', name='uq_subcategory_category_slug'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id', ondelete='CASCADE'))
    slug: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255), default='')

    category: Mapped[CategoryModel] = relationship(back_populates='subcategories')


class ArticleModel(Base):
    __tablename__ = 'articles'

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    primary_category: Mapped[str] = mapped_column(String(100), index=True)
    subcategory: Mapped[str] = mapped_column(String(100), index=True)
    published_at: Mapped[str] = mapped_column(String(10), index=True)
    original_url: Mapped[str] = mapped_column(String(500))
    score_weight: Mapped[float] = mapped_column(Float, default=1.0)


class UserPreferenceModel(Base):
    __tablename__ = 'user_preferences'

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    mode: Mapped[str] = mapped_column(String(20))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    primary_categories: Mapped[list['UserPrimaryCategoryModel']] = relationship(back_populates='preference', cascade='all, delete-orphan')
    subcategories: Mapped[list['UserSubcategoryModel']] = relationship(back_populates='preference', cascade='all, delete-orphan')


class UserPrimaryCategoryModel(Base):
    __tablename__ = 'user_primary_categories'
    __table_args__ = (UniqueConstraint('user_id', 'category_slug', name='uq_user_primary_category'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)
    category_slug: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    preference: Mapped[UserPreferenceModel] = relationship(back_populates='primary_categories')


class UserSubcategoryModel(Base):
    __tablename__ = 'user_subcategories'
    __table_args__ = (UniqueConstraint('user_id', 'subcategory_slug', name='uq_user_subcategory'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)
    subcategory_slug: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    preference: Mapped[UserPreferenceModel] = relationship(back_populates='subcategories')


class ScrapModel(Base):
    __tablename__ = 'scraps'
    __table_args__ = (UniqueConstraint('user_id', 'article_id', name='uq_user_scrap'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey('articles.id', ondelete='CASCADE'), index=True)


class DailyFeedSnapshotModel(Base):
    __tablename__ = 'daily_feed_snapshots'
    __table_args__ = (UniqueConstraint('user_id', 'feed_date', name='uq_daily_feed_snapshot_user_date'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)
    feed_date: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(30), default='generated')
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    preference_mode: Mapped[str] = mapped_column(String(20))
    primary_categories_json: Mapped[str] = mapped_column(Text, default='[]')
    subcategories_json: Mapped[str] = mapped_column(Text, default='[]')
    generation_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    items: Mapped[list['DailyFeedSnapshotItemModel']] = relationship(back_populates='snapshot', cascade='all, delete-orphan')


class DailyFeedSnapshotItemModel(Base):
    __tablename__ = 'daily_feed_snapshot_items'
    __table_args__ = (UniqueConstraint('snapshot_id', 'article_id', name='uq_daily_feed_snapshot_item_article'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey('daily_feed_snapshots.id', ondelete='CASCADE'), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey('articles.id', ondelete='CASCADE'), index=True)
    block_key: Mapped[str] = mapped_column(String(100))
    block_title: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    score_weight: Mapped[float] = mapped_column(Float, default=1.0)

    snapshot: Mapped[DailyFeedSnapshotModel] = relationship(back_populates='items')


class UserArticleReadModel(Base):
    __tablename__ = 'user_article_reads'
    __table_args__ = (UniqueConstraint('user_id', 'article_id', 'snapshot_id', name='uq_user_article_read_snapshot'),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)
    article_id: Mapped[str] = mapped_column(ForeignKey('articles.id', ondelete='CASCADE'), index=True)
    snapshot_id: Mapped[int | None] = mapped_column(ForeignKey('daily_feed_snapshots.id', ondelete='CASCADE'), nullable=True, index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_source: Mapped[str | None] = mapped_column(String(30), nullable=True)


class ExternalIdentityModel(Base):
    __tablename__ = 'external_identities'
    __table_args__ = (
        UniqueConstraint('provider', 'provider_subject', name='uq_external_identity_provider_subject'),
        UniqueConstraint('provider', 'user_id', name='uq_external_identity_provider_user'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(30), index=True)
    provider_subject: Mapped[str] = mapped_column(String(255), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)


class RefreshSessionModel(Base):
    __tablename__ = 'refresh_sessions'

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('user_preferences.user_id', ondelete='CASCADE'), index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    auth_provider: Mapped[str] = mapped_column(String(30), index=True)
    provider_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
