from __future__ import annotations

import json

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
        'slug': 'stock',
        'name': '주식시장',
        'description': '코스피·나스닥·S&P500 등 주식시장 주요 흐름',
        'keywords': ['코스피', '나스닥', 'S&P500'],
        'subcategories': [
            {'slug': 'stock-domestic', 'name': '국내주식', 'description': '국내 상장사·코스피·코스닥 이슈'},
            {'slug': 'stock-overseas', 'name': '해외주식', 'description': '미국·글로벌 증시와 해외 종목'},
            {'slug': 'stock-etf', 'name': 'ETF', 'description': 'ETF 상품과 패시브 투자 흐름'},
            {'slug': 'stock-unlisted', 'name': '비상장주식', 'description': 'IPO 전 기업과 장외시장 이슈'},
        ],
    },
    {
        'slug': 'crypto',
        'name': '가상자산',
        'description': '비트코인·이더리움·알트코인 등 디지털 자산 흐름',
        'keywords': ['비트코인', '이더리움', '알트코인'],
        'subcategories': [
            {'slug': 'crypto-bitcoin', 'name': '비트코인', 'description': '비트코인 가격·ETF·채굴 생태계'},
            {'slug': 'crypto-altcoin', 'name': '알트코인', 'description': '이더리움 외 주요 알트코인'},
            {'slug': 'crypto-defi', 'name': 'DeFi', 'description': '탈중앙 금융 프로토콜과 온체인 유동성'},
            {'slug': 'crypto-nft', 'name': 'NFT', 'description': 'NFT·디지털 컬렉터블·게임 자산'},
        ],
    },
    {
        'slug': 'realestate',
        'name': '부동산',
        'description': '아파트·청약·전세 등 부동산 시장 흐름',
        'keywords': ['아파트', '청약', '전세'],
        'subcategories': [
            {'slug': 'realestate-apt', 'name': '아파트', 'description': '아파트 매매·분양·가격 동향'},
            {'slug': 'realestate-subscription', 'name': '청약', 'description': '청약 제도와 분양 일정'},
            {'slug': 'realestate-lease', 'name': '전세/월세', 'description': '전월세 가격과 임대차 시장'},
            {'slug': 'realestate-commercial', 'name': '상업용', 'description': '오피스·상가·물류센터 등 상업용 부동산'},
        ],
    },
    {
        'slug': 'politics',
        'name': '정치',
        'description': '국회·대통령·정당 중심의 정치 뉴스',
        'keywords': ['국회', '대통령', '정당'],
        'subcategories': [
            {'slug': 'politics-domestic', 'name': '국내정치', 'description': '국회·정당·선거 등 국내 정치'},
            {'slug': 'politics-diplomacy', 'name': '외교', 'description': '외교·안보·정상회담 이슈'},
            {'slug': 'politics-policy', 'name': '정책', 'description': '정부 정책과 입법 이슈'},
        ],
    },
    {
        'slug': 'economy',
        'name': '경제',
        'description': '금리·환율·GDP 등 경제 지표와 금융시장',
        'keywords': ['금리', '환율', 'GDP'],
        'subcategories': [
            {'slug': 'economy-macro', 'name': '거시경제', 'description': '물가·성장률·경기 사이클'},
            {'slug': 'economy-finance', 'name': '금융', 'description': '은행·채권·금리·환율'},
            {'slug': 'economy-trade', 'name': '무역', 'description': '수출입·관세·공급망'},
        ],
    },
    {
        'slug': 'tech',
        'name': 'IT/테크',
        'description': 'AI·반도체·스타트업 등 기술 산업',
        'keywords': ['AI', '반도체', '스타트업'],
        'subcategories': [
            {'slug': 'tech-ai', 'name': 'AI', 'description': 'AI 모델·서비스·인프라'},
            {'slug': 'tech-semiconductor', 'name': '반도체', 'description': '메모리·파운드리·장비'},
            {'slug': 'tech-startup', 'name': '스타트업', 'description': '창업·투자·신규 서비스'},
            {'slug': 'tech-bigtech', 'name': '빅테크', 'description': '글로벌 플랫폼과 대형 IT 기업'},
        ],
    },
    {
        'slug': 'entertainment',
        'name': '연예',
        'description': 'K-POP·드라마·영화 등 엔터테인먼트',
        'keywords': ['K-POP', '드라마', '영화'],
        'subcategories': [
            {'slug': 'entertainment-kpop', 'name': 'K-POP', 'description': '아이돌·음반·공연'},
            {'slug': 'entertainment-drama', 'name': '드라마', 'description': '방송·OTT 드라마'},
            {'slug': 'entertainment-movie', 'name': '영화', 'description': '영화 개봉·흥행·산업'},
        ],
    },
    {
        'slug': 'sports',
        'name': '스포츠',
        'description': '축구·야구·NBA 등 스포츠 주요 뉴스',
        'keywords': ['축구', '야구', 'NBA'],
        'subcategories': [
            {'slug': 'sports-soccer', 'name': '축구', 'description': '국내외 축구 경기와 이적'},
            {'slug': 'sports-baseball', 'name': '야구', 'description': 'KBO·MLB 야구 소식'},
            {'slug': 'sports-basketball', 'name': '농구', 'description': 'KBL·NBA 농구 소식'},
            {'slug': 'sports-esports', 'name': 'e스포츠', 'description': 'e스포츠 리그와 게임 대회'},
        ],
    },
    {
        'slug': 'global',
        'name': '국제',
        'description': '미국·중국·EU 등 글로벌 주요 이슈',
        'keywords': ['미국', '중국', 'EU'],
        'subcategories': [
            {'slug': 'global-us', 'name': '미국', 'description': '미국 정치·경제·사회'},
            {'slug': 'global-china', 'name': '중국', 'description': '중국 정치·경제·사회'},
            {'slug': 'global-europe', 'name': '유럽', 'description': 'EU·유럽 국가 이슈'},
            {'slug': 'global-asia', 'name': '아시아', 'description': '아시아 주요 국가 이슈'},
        ],
    },
    {
        'slug': 'lifestyle',
        'name': '라이프',
        'description': '건강·여행·맛집 등 생활 관심사',
        'keywords': ['건강', '여행', '맛집'],
        'subcategories': [
            {'slug': 'lifestyle-health', 'name': '건강', 'description': '건강관리·의료·웰니스'},
            {'slug': 'lifestyle-travel', 'name': '여행', 'description': '국내외 여행지와 항공'},
            {'slug': 'lifestyle-food', 'name': '맛집', 'description': '외식·맛집·식음료 트렌드'},
        ],
    },
]

ARTICLE_SEED = [
    {
        'id': 'A001',
        'title': '코스피, 반도체 대형주 강세에 상승 마감',
        'summary': '외국인 매수세가 유입되며 코스피가 상승했고 반도체 업종이 지수를 이끌었다.',
        'content': '국내 증시는 반도체 대형주 실적 기대와 원화 안정 흐름에 힘입어 상승 마감했다.',
        'primary_category': 'stock',
        'subcategory': 'stock-domestic',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A001',
        'score_weight': 0.95,
    },
    {
        'id': 'A002',
        'title': '나스닥, AI 투자 기대감에 사상 최고치 근접',
        'summary': '미국 기술주가 AI 인프라 투자 확대 기대를 반영하며 강세를 보였다.',
        'content': 'S&P500과 나스닥은 빅테크 실적 전망과 AI 서버 투자 확대 기대 속에 동반 상승했다.',
        'primary_category': 'stock',
        'subcategory': 'stock-overseas',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A002',
        'score_weight': 0.91,
    },
    {
        'id': 'A003',
        'title': '비트코인 현물 ETF 자금 유입 재개',
        'summary': '기관 자금 유입이 회복되며 비트코인 가격이 다시 반등했다.',
        'content': '비트코인 현물 ETF에는 순유입이 재개됐고 이더리움과 주요 알트코인도 동반 상승했다.',
        'primary_category': 'crypto',
        'subcategory': 'crypto-bitcoin',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A003',
        'score_weight': 0.84,
    },
    {
        'id': 'A004',
        'title': '서울 아파트 전세 매물 부족 심화',
        'summary': '서울 주요 지역에서 전세 매물이 줄고 가격 상승 압력이 커지고 있다.',
        'content': '아파트 입주 물량 감소와 금리 인하 기대가 겹치며 전세와 월세 시장의 불안이 이어지고 있다.',
        'primary_category': 'realestate',
        'subcategory': 'realestate-lease',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A004',
        'score_weight': 0.78,
    },
    {
        'id': 'A005',
        'title': '국회, 청년 주거지원 확대 법안 논의',
        'summary': '여야가 청년층 주거비 부담 완화를 위한 정책 패키지를 논의하고 있다.',
        'content': '국회 상임위는 전세 보증과 월세 세액공제 확대 등 주거 지원 정책을 검토했다.',
        'primary_category': 'politics',
        'subcategory': 'politics-policy',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A005',
        'score_weight': 0.72,
    },
    {
        'id': 'A006',
        'title': '환율 안정에도 기준금리 경로 불확실',
        'summary': '달러-원 환율은 안정됐지만 물가와 성장률 전망이 금리 결정을 어렵게 하고 있다.',
        'content': '한국은행은 물가 둔화와 GDP 성장률, 금융시장 변동성을 함께 보며 통화정책을 조정할 전망이다.',
        'primary_category': 'economy',
        'subcategory': 'economy-finance',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A006',
        'score_weight': 0.88,
    },
    {
        'id': 'A007',
        'title': 'AI 반도체 스타트업 투자 경쟁 확대',
        'summary': '빅테크와 벤처캐피털이 AI 반도체 스타트업 투자에 속도를 내고 있다.',
        'content': 'AI 추론 수요가 늘면서 반도체 설계 스타트업과 데이터센터 인프라 기업에 자금이 몰리고 있다.',
        'primary_category': 'tech',
        'subcategory': 'tech-ai',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A007',
        'score_weight': 0.83,
    },
    {
        'id': 'A008',
        'title': 'K-POP 월드투어, 북미 공연 추가 매진',
        'summary': 'K-POP 대표 그룹의 월드투어 북미 추가 공연이 빠르게 매진됐다.',
        'content': '음반 판매와 공연 수익이 함께 늘며 엔터테인먼트 기업 실적 기대가 커지고 있다.',
        'primary_category': 'entertainment',
        'subcategory': 'entertainment-kpop',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A008',
        'score_weight': 0.80,
    },
    {
        'id': 'A009',
        'title': '프로야구 개막 효과에 스포츠 중계권 경쟁 가열',
        'summary': '야구 흥행과 온라인 시청 증가로 스포츠 중계권 가치가 높아지고 있다.',
        'content': '프로야구와 축구, e스포츠를 포함한 스포츠 콘텐츠 플랫폼 경쟁이 치열해지고 있다.',
        'primary_category': 'sports',
        'subcategory': 'sports-baseball',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A009',
        'score_weight': 0.79,
    },
    {
        'id': 'A010',
        'title': '미국과 중국, EU 관세 협상 앞두고 신경전',
        'summary': '미국·중국·EU가 무역 협상을 앞두고 관세와 공급망 이슈를 조율하고 있다.',
        'content': '글로벌 무역 갈등은 아시아 수출 기업과 유럽 제조업에도 영향을 줄 수 있다는 전망이 나온다.',
        'primary_category': 'global',
        'subcategory': 'global-us',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A010',
        'score_weight': 0.82,
    },
    {
        'id': 'A011',
        'title': '건강 여행 결합한 웰니스 상품 인기',
        'summary': '건강 관리와 여행 경험을 결합한 웰니스 상품 수요가 늘고 있다.',
        'content': '여행업계는 맛집, 숙박, 헬스케어 서비스를 묶은 라이프스타일 상품을 확대하고 있다.',
        'primary_category': 'lifestyle',
        'subcategory': 'lifestyle-travel',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A011',
        'score_weight': 0.77,
    },
]

DEFAULT_PRIMARY = ['stock', 'crypto', 'realestate', 'economy', 'tech']

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
            category_model = CategoryModel(
                slug=slug,
                name=category['name'],
                description=category['description'],
                keywords_json=json.dumps(category.get('keywords', []), ensure_ascii=False),
            )
            session.add(category_model)
            session.flush()
        else:
            category_model.name = category['name']
            category_model.description = category['description']
            category_model.keywords_json = json.dumps(category.get('keywords', []), ensure_ascii=False)

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


def _article_seed_rows() -> list[dict]:
    summarized_seed = [row.model_dump() for row in load_summarized_articles(settings.news_summarizer_dir / 'data')]
    if not summarized_seed:
        return list(ARTICLE_SEED)

    # Keep the committed summarizer output as the primary demo dataset, but always
    # include the small handcrafted mock set too so a fresh Docker DB has enough
    # cross-category content even when the summarizer sample is sparse or filtered.
    return [*summarized_seed, *ARTICLE_SEED]


def _seed_articles(session: Session) -> None:
    existing_ids = set(session.scalars(select(ArticleModel.id)).all())
    for article in _article_seed_rows():
        if article['id'] in existing_ids:
            continue
        session.add(ArticleModel(**article))
        existing_ids.add(article['id'])


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
