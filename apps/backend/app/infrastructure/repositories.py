from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.entities import Article, Category, ExternalIdentity, RefreshSession, Subcategory, UserPreference
from app.domain.enums import PreferenceMode
from app.infrastructure.models import (
    ArticleModel,
    CategoryModel,
    ExternalIdentityModel,
    RefreshSessionModel,
    ScrapModel,
    SubcategoryModel,
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


def _to_category(model: CategoryModel) -> Category:
    return Category(
        id=model.id,
        slug=model.slug,
        name=model.name,
        description=model.description,
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

    def list_by_month(self, month: str) -> list[Article]:
        rows = self.db.scalars(select(ArticleModel).where(ArticleModel.published_at.startswith(month)).order_by(ArticleModel.published_at, ArticleModel.id)).all()
        return [_to_article(row) for row in rows]

    def list_by_date(self, archive_date: str) -> list[Article]:
        rows = self.db.scalars(select(ArticleModel).where(ArticleModel.published_at == archive_date).order_by(ArticleModel.id)).all()
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
