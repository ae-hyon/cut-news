from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.article_ingest_service import load_summarized_articles
from app.common.config import settings
from app.infrastructure.models import (
    ArticleModel,
    CategoryModel,
    ScrapModel,
    SubcategoryModel,
    UserPreferenceModel,
    UserPrimaryCategoryModel,
)

CATEGORY_SEED = [
    {
        'slug': 'sectors',
        'name': '산업 섹터',
        'description': '반도체·모빌리티·바이오처럼 업종별 핵심 흐름',
        'subcategories': [
            {'slug': 'semiconductor', 'name': '반도체', 'description': '메모리·파운드리·장비 기업 이슈'},
            {'slug': 'mobility', 'name': '모빌리티', 'description': '완성차·배터리·전기차 공급망'},
            {'slug': 'bio', 'name': '바이오', 'description': '제약·헬스케어·임상 업데이트'},
        ],
    },
    {
        'slug': 'macro',
        'name': '거시경제',
        'description': '환율·금리·원자재·글로벌 경기 흐름',
        'subcategories': [
            {'slug': 'rates-fx', 'name': '환율·금리', 'description': '환율·채권·기준금리 변동'},
            {'slug': 'energy', 'name': '에너지', 'description': '원유·가스·전력 가격과 수급'},
            {'slug': 'supply-chain', 'name': '공급망', 'description': '무역·물류·원자재 공급망 변화'},
        ],
    },
    {
        'slug': 'assets',
        'name': '투자 자산',
        'description': '주식·해외자산·부동산처럼 바로 투자 판단에 닿는 자산군',
        'subcategories': [
            {'slug': 'domestic-stocks', 'name': '국내 증시', 'description': '코스피·코스닥·상장사 이슈'},
            {'slug': 'global-stocks', 'name': '해외 자산', 'description': '미국 증시·ETF·글로벌 자금 흐름'},
            {'slug': 'real-estate', 'name': '부동산', 'description': '주택·전세·분양·리츠 흐름'},
        ],
    },
    {
        'slug': 'policy',
        'name': '정책·규제',
        'description': '정부·중앙은행·감독당국 결정이 시장에 주는 영향',
        'subcategories': [
            {'slug': 'fiscal', 'name': '정부 정책', 'description': '예산·세제·산업 지원 정책'},
            {'slug': 'central-bank', 'name': '통화정책', 'description': '한은·연준·기준금리 메시지'},
            {'slug': 'regulation', 'name': '규제', 'description': '금융위·금감원·공시·감독 이슈'},
        ],
    },
]

ARTICLE_SEED = [
    {
        'id': 'A001',
        'title': '요즘 집 구할 때 노룩 전세가 늘어났다',
        'summary': '서울 아파트 전세가 상승과 매물 부족으로 집을 보지 않고 계약하는 사례가 늘고 있다.',
        'content': '서울 아파트 전세가 변동률이 작년보다 5배 이상 가파르게 상승하며, 매물 부족으로 집도 안 보고 계약하는 현상이 확산되고 있다.',
        'primary_category': 'assets',
        'subcategory': 'real-estate',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A001',
        'score_weight': 0.95,
    },
    {
        'id': 'A002',
        'title': '주택시장 격차 확대 전망',
        'summary': '전문가들은 매매보다 전세 가격 상승 폭이 커지며 지역 간 격차가 먼저 확대될 것으로 본다.',
        'content': '2026년 주택시장은 금리 인하 기대와 공급 부족이 겹치며 가격보다 격차 확대가 먼저 나타날 수 있다는 전망이 나왔다.',
        'primary_category': 'assets',
        'subcategory': 'real-estate',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A002',
        'score_weight': 0.91,
    },
    {
        'id': 'A003',
        'title': '전국 매매 0.05%·전세 0.09% 상승',
        'summary': '전국 주간 주택 가격이 소폭 상승했고 전세 상승률이 매매를 웃돌았다.',
        'content': '한국부동산원 집계 결과 전국 매매가격은 0.05%, 전세가격은 0.09% 상승했다.',
        'primary_category': 'macro',
        'subcategory': 'rates-fx',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A003',
        'score_weight': 0.84,
    },
    {
        'id': 'A004',
        'title': '부동산감독원 설립 및 청년 주거지원 강화',
        'summary': '정부가 부동산감독원 설립과 청년 주거지원 강화를 포함한 대책을 검토 중이다.',
        'content': '정부는 시장 교란 행위 대응과 청년층 주거 안정을 위해 감독 기능 강화와 지원책 확대를 추진하고 있다.',
        'primary_category': 'policy',
        'subcategory': 'regulation',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A004',
        'score_weight': 0.78,
    },
    {
        'id': 'A005',
        'title': '국토부, 공동주택 공시가격 열람 및 의견 청취',
        'summary': '국토부가 공동주택 공시가격(안) 열람과 의견 제출을 받고 있다.',
        'content': '국토교통부는 공동주택 공시가격에 대한 국민 의견을 청취하기 위해 열람 기간을 운영한다.',
        'primary_category': 'policy',
        'subcategory': 'fiscal',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A005',
        'score_weight': 0.72,
    },
    {
        'id': 'A006',
        'title': '삼성전자·SK하이닉스, HBM 증설 경쟁 본격화',
        'summary': 'HBM 수요 확대에 맞춰 메모리 업계의 증설 경쟁이 빨라지고 있다.',
        'content': 'AI 서버 투자 확대와 고대역폭 메모리 수요 증가로 국내 반도체 업계의 설비 투자와 고객사 확보 경쟁이 심화하고 있다.',
        'primary_category': 'sectors',
        'subcategory': 'semiconductor',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A006',
        'score_weight': 0.88,
    },
    {
        'id': 'A007',
        'title': '현대차, 중국 전략 전기차 공개',
        'summary': '현대차가 중국 시장 맞춤형 전기차를 공개하며 판매 반등을 노린다.',
        'content': '중국 전기차 경쟁 심화 속에서 현대차가 현지 전략 모델과 배터리 공급망 최적화를 통해 판매 회복을 추진하고 있다.',
        'primary_category': 'sectors',
        'subcategory': 'mobility',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A007',
        'score_weight': 0.83,
    },
]

DEFAULT_PRIMARY = ['sectors', 'macro', 'assets', 'policy']


def _sync_categories(session: Session) -> None:
    desired = {category['slug']: category for category in CATEGORY_SEED}
    existing = {category.slug: category for category in session.scalars(select(CategoryModel)).all()}

    for slug, category_model in list(existing.items()):
        if slug not in desired:
            session.delete(category_model)

    session.flush()

    for slug, category in desired.items():
        category_model = existing.get(slug)
        if category_model is None:
            category_model = CategoryModel(slug=slug, name=category['name'], description=category['description'])
            session.add(category_model)
            session.flush()
        else:
            category_model.name = category['name']
            category_model.description = category['description']

        existing_subs = {sub.slug: sub for sub in category_model.subcategories}
        desired_subs = {sub['slug']: sub for sub in category['subcategories']}

        for sub_slug, sub_model in list(existing_subs.items()):
            if sub_slug not in desired_subs:
                session.delete(sub_model)

        session.flush()

        for sub_slug, sub in desired_subs.items():
            sub_model = existing_subs.get(sub_slug)
            if sub_model is None:
                session.add(
                    SubcategoryModel(
                        category_id=category_model.id,
                        slug=sub_slug,
                        name=sub['name'],
                        description=sub['description'],
                    )
                )
            else:
                sub_model.name = sub['name']
                sub_model.description = sub['description']


def _seed_articles(session: Session) -> None:
    has_articles = session.scalar(select(ArticleModel.id)) is not None
    if has_articles:
        return

    article_seed = [row.model_dump() for row in load_summarized_articles(settings.news_summarizer_dir / 'data')]
    if not article_seed:
        article_seed = ARTICLE_SEED
    for article in article_seed:
        session.add(ArticleModel(**article))


def _sync_demo_user(session: Session) -> None:
    preference = session.get(UserPreferenceModel, 'demo-user')
    if preference is None:
        preference = UserPreferenceModel(user_id='demo-user', mode='wide', onboarding_completed=True)
        session.add(preference)
        session.flush()
    else:
        preference.mode = 'wide'
        preference.onboarding_completed = True

    session.query(UserPrimaryCategoryModel).filter(UserPrimaryCategoryModel.user_id == 'demo-user').delete()
    for idx, slug in enumerate(DEFAULT_PRIMARY):
        session.add(UserPrimaryCategoryModel(user_id='demo-user', category_slug=slug, sort_order=idx))


def _seed_scraps(session: Session) -> None:
    has_scraps = session.scalar(select(ScrapModel.id)) is not None
    if has_scraps:
        return

    seeded_scrap_targets = [
        session.scalar(select(ArticleModel.id).order_by(ArticleModel.published_at.desc(), ArticleModel.id.asc())),
        session.scalar(select(ArticleModel.id).order_by(ArticleModel.published_at.desc(), ArticleModel.id.asc()).offset(1)),
    ]
    for article_id in [target for target in seeded_scrap_targets if target]:
        session.add(ScrapModel(user_id='demo-user', article_id=article_id))


def seed_database(session: Session) -> None:
    _sync_categories(session)
    _seed_articles(session)
    _sync_demo_user(session)
    _seed_scraps(session)
    session.commit()
