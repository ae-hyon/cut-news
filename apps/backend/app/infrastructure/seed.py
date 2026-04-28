from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        'slug': 'economy',
        'name': '경제',
        'description': '거시경제, 금융, 부동산 등 경제 전반',
        'subcategories': [
            {'slug': 'stocks', 'name': '주식시장', 'description': '국내외 증시, ETF, 종목 이슈'},
            {'slug': 'real-estate', 'name': '부동산', 'description': '주택, 전세, 분양, 정책'},
            {'slug': 'macro', 'name': '거시경제', 'description': '금리, 환율, 경기'},
        ],
    },
    {
        'slug': 'politics',
        'name': '정치',
        'description': '정부, 국회, 외교안보 이슈',
        'subcategories': [
            {'slug': 'policy', 'name': '정책', 'description': '정부 정책, 제도 개편'},
            {'slug': 'assembly', 'name': '국회', 'description': '법안, 정당, 청문회'},
            {'slug': 'diplomacy', 'name': '외교', 'description': '정상회담, 국제관계'},
        ],
    },
    {
        'slug': 'entertainment',
        'name': '연예',
        'description': '방송, 영화, 음악, 셀럽',
        'subcategories': [
            {'slug': 'broadcast', 'name': '방송', 'description': '예능, 드라마, OTT'},
            {'slug': 'music', 'name': '음악', 'description': '가요, 공연, 차트'},
            {'slug': 'film', 'name': '영화', 'description': '영화, 배우, 시사회'},
        ],
    },
    {
        'slug': 'tech',
        'name': '테크',
        'description': 'AI, 스타트업, 반도체',
        'subcategories': [
            {'slug': 'ai', 'name': 'AI', 'description': '생성형 AI, 모델, 서비스'},
            {'slug': 'startup', 'name': '스타트업', 'description': '투자, 신사업'},
            {'slug': 'semiconductor', 'name': '반도체', 'description': '메모리, 파운드리'},
        ],
    },
    {
        'slug': 'sports',
        'name': '스포츠',
        'description': '축구, 야구, e스포츠',
        'subcategories': [
            {'slug': 'soccer', 'name': '축구', 'description': '국내외 축구'},
            {'slug': 'baseball', 'name': '야구', 'description': 'KBO, MLB'},
            {'slug': 'esports', 'name': 'e스포츠', 'description': '리그, 선수, 대회'},
        ],
    },
]

ARTICLE_SEED = [
    {
        'id': 'A001',
        'title': "요즘 집 구할 때 '노룩 전세' 알죠? 한 달 새 전세보증금 1억 껑충",
        'summary': '서울 아파트 전세가 상승과 매물 부족으로 집을 보지 않고 계약하는 사례가 늘고 있다.',
        'content': '서울 아파트 전세가 변동률이 작년보다 5배 이상 가파르게 상승하며, 매물 부족으로 집도 안 보고 계약하는 현상이 확산되고 있다.',
        'primary_category': 'economy',
        'subcategory': 'real-estate',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A001',
        'score_weight': 0.95,
    },
    {
        'id': 'A002',
        'title': '집값 2% 오르고, 전세는 5% 뛴다… 2026년 주택시장 격차 확대',
        'summary': '전문가들은 매매보다 전세 가격 상승 폭이 커지며 지역 간 격차가 먼저 확대될 것으로 본다.',
        'content': '2026년 주택시장은 금리 인하 기대와 공급 부족이 겹치며 가격보다 격차 확대가 먼저 나타날 수 있다는 전망이 나왔다.',
        'primary_category': 'economy',
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
        'primary_category': 'economy',
        'subcategory': 'macro',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A003',
        'score_weight': 0.84,
    },
    {
        'id': 'A004',
        'title': '부동산감독원 설립 및 청년 주거지원 강화',
        'summary': '정부가 부동산감독원 설립과 청년 주거지원 강화를 포함한 대책을 검토 중이다.',
        'content': '정부는 시장 교란 행위 대응과 청년층 주거 안정을 위해 감독 기능 강화와 지원책 확대를 추진하고 있다.',
        'primary_category': 'politics',
        'subcategory': 'policy',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A004',
        'score_weight': 0.78,
    },
    {
        'id': 'A005',
        'title': '국토부, 공동주택 공시가격 열람 및 의견 청취 4월 6일 마감',
        'summary': '국토부가 공동주택 공시가격(안) 열람과 의견 제출을 4월 6일까지 받는다.',
        'content': '국토교통부는 공동주택 공시가격에 대한 국민 의견을 청취하기 위해 열람 기간을 운영한다.',
        'primary_category': 'politics',
        'subcategory': 'policy',
        'published_at': '2026-04-14',
        'original_url': 'https://example.com/articles/A005',
        'score_weight': 0.72,
    },
    {
        'id': 'A006',
        'title': 'AI가 블록 비중을 조정해 오늘의 뉴스판을 구성한다',
        'summary': '사용자 관심사와 최근 반응을 바탕으로 AI가 홈 피드 블록 가중치를 조정한다.',
        'content': '관심 카테고리, 스크랩 이력, 최근 소비 패턴을 반영해 뉴스 블록 노출 비중이 달라지는 개인화 로직을 적용한다.',
        'primary_category': 'tech',
        'subcategory': 'ai',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A006',
        'score_weight': 0.88,
    },
    {
        'id': 'A007',
        'title': '카카오 로그인 도입으로 매일 블록 받아보기 간소화',
        'summary': '카카오 로그인으로 온보딩 완료 후 매일 뉴스 블록을 받아보는 흐름을 단순화한다.',
        'content': '간편 로그인 이후 사용자 선호도를 저장하고 매일 개인화된 뉴스 블록을 제공하는 흐름이 정리됐다.',
        'primary_category': 'tech',
        'subcategory': 'startup',
        'published_at': '2026-04-15',
        'original_url': 'https://example.com/articles/A007',
        'score_weight': 0.83,
    },
]


def seed_database(session: Session) -> None:
    has_category = session.scalar(select(CategoryModel.id)) is not None
    if not has_category:
        for category in CATEGORY_SEED:
            category_model = CategoryModel(slug=category['slug'], name=category['name'], description=category['description'])
            session.add(category_model)
            session.flush()
            for sub in category['subcategories']:
                session.add(SubcategoryModel(category_id=category_model.id, slug=sub['slug'], name=sub['name'], description=sub['description']))

    has_articles = session.scalar(select(ArticleModel.id)) is not None
    if not has_articles:
        for article in ARTICLE_SEED:
            session.add(ArticleModel(**article))

    has_demo_user = session.scalar(select(UserPreferenceModel.user_id).where(UserPreferenceModel.user_id == 'demo-user')) is not None
    if not has_demo_user:
        session.add(UserPreferenceModel(user_id='demo-user', mode='wide', onboarding_completed=True))
        session.flush()
        for idx, slug in enumerate(['economy', 'politics', 'tech']):
            session.add(UserPrimaryCategoryModel(user_id='demo-user', category_slug=slug, sort_order=idx))

    has_scraps = session.scalar(select(ScrapModel.id)) is not None
    if not has_scraps:
        session.add(ScrapModel(user_id='demo-user', article_id='A001'))
        session.add(ScrapModel(user_id='demo-user', article_id='A004'))

    session.commit()
