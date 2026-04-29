from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.database import Base
from app.infrastructure.models import CategoryModel, SubcategoryModel, UserPreferenceModel, UserPrimaryCategoryModel
from app.infrastructure.seed import DEFAULT_PRIMARY, seed_database


def make_session() -> Session:
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def test_seed_database_reconciles_existing_categories_and_demo_user_defaults(monkeypatch):
    monkeypatch.setattr('app.infrastructure.seed.load_summarized_articles', lambda *_args, **_kwargs: [])
    session = make_session()

    old_category = CategoryModel(slug='economy', name='경제', description='old')
    session.add(old_category)
    session.flush()
    session.add(SubcategoryModel(category_id=old_category.id, slug='stocks', name='주식시장', description='old sub'))
    session.add(UserPreferenceModel(user_id='demo-user', mode='narrow', onboarding_completed=False))
    session.add(UserPrimaryCategoryModel(user_id='demo-user', category_slug='economy', sort_order=0))
    session.commit()

    seed_database(session)

    categories = session.scalars(select(CategoryModel).order_by(CategoryModel.slug)).all()
    assert [category.slug for category in categories] == ['assets', 'macro', 'policy', 'sectors']
    assert session.scalar(select(CategoryModel.id).where(CategoryModel.slug == 'economy')) is None

    demo_user = session.get(UserPreferenceModel, 'demo-user')
    assert demo_user is not None
    assert demo_user.mode == 'wide'
    assert demo_user.onboarding_completed is True

    primary = session.scalars(
        select(UserPrimaryCategoryModel.category_slug)
        .where(UserPrimaryCategoryModel.user_id == 'demo-user')
        .order_by(UserPrimaryCategoryModel.sort_order)
    ).all()
    assert primary == DEFAULT_PRIMARY
