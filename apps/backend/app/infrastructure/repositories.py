from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.entities import Article, Category, DailyFeedSnapshot, DailyFeedSnapshotItem, ExternalIdentity, RefreshSession, Subcategory, UserPreference
from app.domain.enums import PreferenceMode
from app.infrastructure.models import (
    ArticleModel,
    CategoryModel,
    DailyFeedSnapshotItemModel,
    DailyFeedSnapshotModel,
    ExternalIdentityModel,
    RefreshSessionModel,
    ScrapModel,
    SubcategoryModel,
    UserArticleReadModel,
    UserPreferenceModel,
    UserPrimaryCategoryModel,
    UserSubcategoryModel,
)


def _to_subcategory(model: SubcategoryModel, category_slug: str) -> Subcategory:
    return Subcategory(
        id=model.id,
        slug=model.slug,
        name=model.name,
        description=model.description,
        category_slug=category_slug,
    )


def _category_keywords(model: CategoryModel) -> list[str]:
    try:
        payload = json.loads(model.keywords_json or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _to_category(model: CategoryModel) -> Category:
    return Category(
        id=model.id,
        slug=model.slug,
        name=model.name,
        description=model.description,
        keywords=_category_keywords(model),
        subcategories=[_to_subcategory(sub, model.slug) for sub in sorted(model.subcategories, key=lambda item: item.id)],
    )


def _to_article(model: ArticleModel) -> Article:
    return Article(
        id=model.id,
        title=model.title,
        summary=model.summary,
        content=model.content,
        primary_category=model.primary_category,
        subcategory=model.subcategory,
        published_at=model.published_at,
        original_url=model.original_url,
        score_weight=model.score_weight,
    )


def _to_preference(model: UserPreferenceModel) -> UserPreference:
    return UserPreference(
        user_id=model.user_id,
        mode=PreferenceMode(model.mode),
        primary_categories=[item.category_slug for item in sorted(model.primary_categories, key=lambda x: x.sort_order)],
        subcategories=[item.subcategory_slug for item in sorted(model.subcategories, key=lambda x: x.sort_order)],
        onboarding_completed=model.onboarding_completed,
    )


def _json_list(value: str | None) -> list[str]:
    try:
        payload = json.loads(value or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [str(item) for item in payload]


def _with_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _to_snapshot_item(model: DailyFeedSnapshotItemModel) -> DailyFeedSnapshotItem:
    return DailyFeedSnapshotItem(
        id=model.id,
        snapshot_id=model.snapshot_id,
        article_id=model.article_id,
        block_key=model.block_key,
        block_title=model.block_title,
        sort_order=model.sort_order,
        score_weight=model.score_weight,
    )


def _to_snapshot(model: DailyFeedSnapshotModel) -> DailyFeedSnapshot:
    return DailyFeedSnapshot(
        id=model.id,
        user_id=model.user_id,
        feed_date=model.feed_date,
        status=model.status,
        generated_at=_with_utc(model.generated_at),
        first_viewed_at=_with_utc(model.first_viewed_at),
        completed_at=_with_utc(model.completed_at),
        preference_mode=PreferenceMode(model.preference_mode),
        primary_categories=_json_list(model.primary_categories_json),
        subcategories=_json_list(model.subcategories_json),
        generation_source=model.generation_source,
        items=[_to_snapshot_item(item) for item in sorted(model.items, key=lambda item: item.sort_order)],
    )


def _to_external_identity(model: ExternalIdentityModel) -> ExternalIdentity:
    return ExternalIdentity(provider=model.provider, provider_subject=model.provider_subject, user_id=model.user_id)


def _to_refresh_session(model: RefreshSessionModel) -> RefreshSession:
    return RefreshSession(
        session_id=model.session_id,
        user_id=model.user_id,
        refresh_token_hash=model.refresh_token_hash,
        auth_provider=model.auth_provider,
        provider_subject=model.provider_subject,
        revoked=model.revoked,
        issued_at=model.issued_at,
        last_used_at=model.last_used_at,
        revoked_at=model.revoked_at,
    )


class SqlAlchemyCategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(self) -> list[Category]:
        items = self.db.scalars(select(CategoryModel).options(selectinload(CategoryModel.subcategories)).order_by(CategoryModel.id)).all()
        return [_to_category(item) for item in items]

    def get_by_slug(self, slug: str) -> Category | None:
        item = self.db.scalar(select(CategoryModel).options(selectinload(CategoryModel.subcategories)).where(CategoryModel.slug == slug))
        return _to_category(item) if item else None

    def exists_by_slug(self, slug: str) -> bool:
        return self.db.scalar(select(CategoryModel.id).where(CategoryModel.slug == slug)) is not None

    def valid_subcategories(self, category_slug: str) -> set[str]:
        rows = self.db.scalars(
            select(SubcategoryModel.slug).join(CategoryModel, SubcategoryModel.category_id == CategoryModel.id).where(CategoryModel.slug == category_slug)
        ).all()
        return set(rows)


class SqlAlchemyArticleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, article_id: str) -> Article | None:
        item = self.db.get(ArticleModel, article_id)
        return _to_article(item) if item else None

    def list_by_primary(self, category_slug: str) -> list[Article]:
        rows = self.db.scalars(select(ArticleModel).where(ArticleModel.primary_category == category_slug).order_by(ArticleModel.published_at.desc(), ArticleModel.id)).all()
        return [_to_article(row) for row in rows]

    def list_by_primary_and_subcategories(self, category_slug: str, subcategories: list[str]) -> list[Article]:
        rows = self.db.scalars(
            select(ArticleModel)
            .where(ArticleModel.primary_category == category_slug, ArticleModel.subcategory.in_(subcategories))
            .order_by(ArticleModel.published_at.desc(), ArticleModel.id)
        ).all()
        return [_to_article(row) for row in rows]

    def list_by_date(self, archive_date: str) -> list[Article]:
        rows = self.db.scalars(select(ArticleModel).where(ArticleModel.published_at == archive_date).order_by(ArticleModel.published_at.desc(), ArticleModel.id)).all()
        return [_to_article(row) for row in rows]

    def list_by_month(self, archive_month: str) -> list[Article]:
        rows = self.db.scalars(
            select(ArticleModel)
            .where(ArticleModel.published_at.like(f'{archive_month}-%'))
            .order_by(ArticleModel.published_at.desc(), ArticleModel.id)
        ).all()
        return [_to_article(row) for row in rows]


class SqlAlchemyUserPreferenceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str) -> UserPreference | None:
        item = self.db.scalar(
            select(UserPreferenceModel)
            .options(selectinload(UserPreferenceModel.primary_categories), selectinload(UserPreferenceModel.subcategories))
            .where(UserPreferenceModel.user_id == user_id)
        )
        return _to_preference(item) if item else None

    def list_onboarded_user_ids(self) -> list[str]:
        rows = self.db.scalars(
            select(UserPreferenceModel.user_id)
            .where(UserPreferenceModel.onboarding_completed.is_(True))
            .order_by(UserPreferenceModel.user_id)
        ).all()
        return list(rows)

    def save(self, preference: UserPreference) -> UserPreference:
        item = self.db.get(UserPreferenceModel, preference.user_id)
        if not item:
            item = UserPreferenceModel(
                user_id=preference.user_id,
                mode=preference.mode.value,
                onboarding_completed=preference.onboarding_completed,
            )
            self.db.add(item)
            self.db.flush()

        item.mode = preference.mode.value
        item.onboarding_completed = preference.onboarding_completed

        self.db.execute(delete(UserPrimaryCategoryModel).where(UserPrimaryCategoryModel.user_id == preference.user_id))
        self.db.execute(delete(UserSubcategoryModel).where(UserSubcategoryModel.user_id == preference.user_id))
        self.db.flush()

        for idx, slug in enumerate(preference.primary_categories):
            self.db.add(UserPrimaryCategoryModel(user_id=preference.user_id, category_slug=slug, sort_order=idx))
        for idx, slug in enumerate(preference.subcategories):
            self.db.add(UserSubcategoryModel(user_id=preference.user_id, subcategory_slug=slug, sort_order=idx))

        self.db.commit()
        self.db.expire_all()
        return self.get(preference.user_id)


class SqlAlchemyScrapRepository:
    def __init__(self, db: Session):
        self.db = db

    def add(self, user_id: str, article_id: str) -> None:
        if not self.exists(user_id, article_id):
            self.db.add(ScrapModel(user_id=user_id, article_id=article_id))
            self.db.commit()

    def remove(self, user_id: str, article_id: str) -> None:
        self.db.execute(delete(ScrapModel).where(ScrapModel.user_id == user_id, ScrapModel.article_id == article_id))
        self.db.commit()

    def exists(self, user_id: str, article_id: str) -> bool:
        return self.db.scalar(select(ScrapModel.id).where(ScrapModel.user_id == user_id, ScrapModel.article_id == article_id)) is not None

    def list_article_ids(self, user_id: str) -> list[str]:
        rows = self.db.scalars(select(ScrapModel.article_id).where(ScrapModel.user_id == user_id).order_by(ScrapModel.article_id)).all()
        return list(rows)


class SqlAlchemyDailyFeedSnapshotRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, snapshot_id: int) -> DailyFeedSnapshot | None:
        item = self.db.scalar(select(DailyFeedSnapshotModel).options(selectinload(DailyFeedSnapshotModel.items)).where(DailyFeedSnapshotModel.id == snapshot_id))
        return _to_snapshot(item) if item else None

    def get_by_user_date(self, user_id: str, feed_date: str) -> DailyFeedSnapshot | None:
        item = self.db.scalar(
            select(DailyFeedSnapshotModel)
            .options(selectinload(DailyFeedSnapshotModel.items))
            .where(DailyFeedSnapshotModel.user_id == user_id, DailyFeedSnapshotModel.feed_date == feed_date)
        )
        return _to_snapshot(item) if item else None

    def list_by_user_month(self, user_id: str, month: str) -> list[DailyFeedSnapshot]:
        rows = self.db.scalars(
            select(DailyFeedSnapshotModel)
            .options(selectinload(DailyFeedSnapshotModel.items))
            .where(DailyFeedSnapshotModel.user_id == user_id, DailyFeedSnapshotModel.feed_date.like(f'{month}-%'))
            .order_by(DailyFeedSnapshotModel.feed_date.desc())
        ).all()
        return [_to_snapshot(row) for row in rows]

    def save(self, snapshot: DailyFeedSnapshot) -> DailyFeedSnapshot:
        item = self.db.scalar(
            select(DailyFeedSnapshotModel)
            .options(selectinload(DailyFeedSnapshotModel.items))
            .where(DailyFeedSnapshotModel.user_id == snapshot.user_id, DailyFeedSnapshotModel.feed_date == snapshot.feed_date)
        )
        if not item:
            item = DailyFeedSnapshotModel(
                user_id=snapshot.user_id,
                feed_date=snapshot.feed_date,
                status=snapshot.status,
                generated_at=snapshot.generated_at,
                first_viewed_at=snapshot.first_viewed_at,
                completed_at=snapshot.completed_at,
                preference_mode=snapshot.preference_mode.value,
                primary_categories_json=json.dumps(snapshot.primary_categories, ensure_ascii=False),
                subcategories_json=json.dumps(snapshot.subcategories, ensure_ascii=False),
                generation_source=snapshot.generation_source,
            )
            self.db.add(item)
            self.db.flush()
        else:
            item.status = snapshot.status
            item.generated_at = snapshot.generated_at
            item.first_viewed_at = snapshot.first_viewed_at
            item.completed_at = snapshot.completed_at
            item.preference_mode = snapshot.preference_mode.value
            item.primary_categories_json = json.dumps(snapshot.primary_categories, ensure_ascii=False)
            item.subcategories_json = json.dumps(snapshot.subcategories, ensure_ascii=False)
            item.generation_source = snapshot.generation_source
            self.db.flush()

        self.replace_items(item.id, snapshot.items, commit=False)
        self.db.commit()
        self.db.expire_all()
        saved = self.get_by_user_date(snapshot.user_id, snapshot.feed_date)
        if saved is None:
            raise RuntimeError('Saved daily feed snapshot could not be reloaded')
        return saved

    def replace_items(self, snapshot_id: int, items: list[DailyFeedSnapshotItem], commit: bool = True) -> None:
        self.db.execute(delete(DailyFeedSnapshotItemModel).where(DailyFeedSnapshotItemModel.snapshot_id == snapshot_id))
        for item in items:
            self.db.add(
                DailyFeedSnapshotItemModel(
                    snapshot_id=snapshot_id,
                    article_id=item.article_id,
                    block_key=item.block_key,
                    block_title=item.block_title,
                    sort_order=item.sort_order,
                    score_weight=item.score_weight,
                )
            )
        if commit:
            self.db.commit()

    def mark_viewed(self, snapshot_id: int, viewed_at: datetime) -> DailyFeedSnapshot:
        item = self.db.get(DailyFeedSnapshotModel, snapshot_id)
        if item is None:
            raise ValueError('Daily feed snapshot not found')
        if item.first_viewed_at is None:
            item.first_viewed_at = viewed_at
        if item.status == 'generated':
            item.status = 'viewed'
        self.db.commit()
        self.db.expire_all()
        loaded = self.db.scalar(select(DailyFeedSnapshotModel).options(selectinload(DailyFeedSnapshotModel.items)).where(DailyFeedSnapshotModel.id == snapshot_id))
        if loaded is None:
            raise RuntimeError('Viewed daily feed snapshot could not be reloaded')
        return _to_snapshot(loaded)


class SqlAlchemyUserArticleReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def mark_read(self, user_id: str, article_id: str, snapshot_id: int | None, read_at: datetime, read_source: str | None = None) -> None:
        item = self.db.scalar(
            select(UserArticleReadModel).where(
                UserArticleReadModel.user_id == user_id,
                UserArticleReadModel.article_id == article_id,
                UserArticleReadModel.snapshot_id == snapshot_id,
            )
        )
        if item is None:
            item = UserArticleReadModel(
                user_id=user_id,
                article_id=article_id,
                snapshot_id=snapshot_id,
                opened_at=read_at,
                read_at=read_at,
                read_source=read_source,
            )
            self.db.add(item)
        else:
            opened_at = _with_utc(item.opened_at)
            if opened_at is None or read_at < opened_at:
                item.opened_at = read_at
            item.read_at = item.read_at or read_at
            item.read_source = item.read_source or read_source
        self.db.commit()

    def list_read_article_ids(self, user_id: str, snapshot_id: int) -> set[str]:
        rows = self.db.scalars(
            select(UserArticleReadModel.article_id).where(
                UserArticleReadModel.user_id == user_id,
                UserArticleReadModel.snapshot_id == snapshot_id,
                UserArticleReadModel.read_at.is_not(None),
            )
        ).all()
        return set(rows)


class SqlAlchemyExternalIdentityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_provider_subject(self, provider: str, provider_subject: str) -> ExternalIdentity | None:
        item = self.db.scalar(
            select(ExternalIdentityModel).where(
                ExternalIdentityModel.provider == provider,
                ExternalIdentityModel.provider_subject == provider_subject,
            )
        )
        return _to_external_identity(item) if item else None

    def save(self, identity: ExternalIdentity) -> ExternalIdentity:
        item = self.db.scalar(
            select(ExternalIdentityModel).where(
                ExternalIdentityModel.provider == identity.provider,
                ExternalIdentityModel.provider_subject == identity.provider_subject,
            )
        )
        if not item:
            item = ExternalIdentityModel(provider=identity.provider, provider_subject=identity.provider_subject, user_id=identity.user_id)
            self.db.add(item)
        else:
            item.user_id = identity.user_id
        self.db.commit()
        return self.get_by_provider_subject(identity.provider, identity.provider_subject)


class SqlAlchemyRefreshSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token_hash(self, refresh_token_hash: str) -> RefreshSession | None:
        item = self.db.scalar(select(RefreshSessionModel).where(RefreshSessionModel.refresh_token_hash == refresh_token_hash))
        return _to_refresh_session(item) if item else None

    def save(self, session: RefreshSession) -> RefreshSession:
        item = self.db.get(RefreshSessionModel, session.session_id)
        if not item:
            item = RefreshSessionModel(
                session_id=session.session_id,
                user_id=session.user_id,
                refresh_token_hash=session.refresh_token_hash,
                auth_provider=session.auth_provider,
                provider_subject=session.provider_subject,
                revoked=session.revoked,
                issued_at=session.issued_at,
                last_used_at=session.last_used_at,
                revoked_at=session.revoked_at,
            )
            self.db.add(item)
        else:
            item.user_id = session.user_id
            item.refresh_token_hash = session.refresh_token_hash
            item.auth_provider = session.auth_provider
            item.provider_subject = session.provider_subject
            item.revoked = session.revoked
            item.issued_at = session.issued_at
            item.last_used_at = session.last_used_at
            item.revoked_at = session.revoked_at
        self.db.commit()
        return self.get_by_token_hash(session.refresh_token_hash)

    def revoke_by_token_hash(self, refresh_token_hash: str) -> None:
        item = self.db.scalar(select(RefreshSessionModel).where(RefreshSessionModel.refresh_token_hash == refresh_token_hash))
        if item and not item.revoked:
            item.revoked = True
            item.revoked_at = datetime.now(UTC)
            self.db.commit()
