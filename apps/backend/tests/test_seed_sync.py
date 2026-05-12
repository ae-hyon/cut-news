from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.application.services.article_ingest_service import ArticleIngestRow
from app.infrastructure.database import Base
from app.infrastructure.models import (
    ArticleModel,
    CategoryModel,
    ScrapModel,
    SubcategoryModel,
    UserPreferenceModel,
    UserPrimaryCategoryModel,
)
from app.infrastructure.seed import ARTICLE_SEED, DEFAULT_PRIMARY, seed_database


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

    article_ids = session.scalars(select(ArticleModel.id).order_by(ArticleModel.id)).all()
    assert article_ids == [article['id'] for article in ARTICLE_SEED]

    scrap_count = session.query(ScrapModel).count()
    assert scrap_count == 2


def test_seed_database_includes_committed_summarizer_rows_and_mock_fallback(monkeypatch):
    summarized_article = {
        'id': 'SUM-001',
        'title': '환율 급등에 수출기업 비용 부담 확대',
        'summary': '원화 약세로 원자재 수입 비용과 환헤지 비용이 동시에 늘고 있다.',
        'content': '환율 변동성이 커지며 수출입 기업의 자금 운용 부담이 확대되고 있다.',
        'primary_category': 'macro',
        'subcategory': 'rates-fx',
        'published_at': '2026-04-24',
        'original_url': 'https://example.com/summarizer/001',
        'score_weight': 0.97,
    }
    monkeypatch.setattr('app.infrastructure.seed.load_summarized_articles', lambda *_args, **_kwargs: [ArticleIngestRow(**summarized_article)])
    session = make_session()

    seed_database(session)
    seed_database(session)

    article_ids = session.scalars(select(ArticleModel.id).order_by(ArticleModel.id)).all()
    assert article_ids == sorted(['SUM-001', *[article['id'] for article in ARTICLE_SEED]])
    assert session.query(ArticleModel).count() == len(ARTICLE_SEED) + 1
    assert session.query(ScrapModel).count() == 2
