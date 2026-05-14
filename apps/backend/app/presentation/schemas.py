from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

HEADLINE_LIMITS = {
    'headline_34': (29, 34),
    'headline_58': (50, 58),
    'headline_89': (76, 89),
}


def normalize_text(value: str) -> str:
    return ' '.join(value.split())


from app.domain.entities import Article, Category, Subcategory, UserPreference
from app.domain.enums import PreferenceMode


class HealthResponseSchema(BaseModel):
    status: str
    app: str
    version: str


class SubcategoryResponseSchema(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    category_slug: str

    @classmethod
    def from_entity(cls, entity: Subcategory) -> 'SubcategoryResponseSchema':
        return cls.model_validate(entity.model_dump())


class CategoryResponseSchema(BaseModel):
    id: int
    slug: str
    name: str
    description: str
    keywords: list[str]
    subcategories: list[SubcategoryResponseSchema]

    @classmethod
    def from_entity(cls, entity: Category) -> 'CategoryResponseSchema':
        return cls(
            id=entity.id,
            slug=entity.slug,
            name=entity.name,
            description=entity.description,
            keywords=entity.keywords,
            subcategories=[SubcategoryResponseSchema.from_entity(item) for item in entity.subcategories],
        )


class UserPreferenceUpdateRequestSchema(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra={
            'examples': [
                {
                    'mode': 'wide',
                    'primary_categories': ['macro', 'sectors', 'policy'],
                    'subcategories': [],
                },
                {
                    'mode': 'narrow',
                    'primary_categories': ['macro'],
                    'subcategories': ['rates-fx'],
                },
            ]
        },
    )

    mode: Literal['wide', 'narrow']
    primary_categories: list[str] = Field(default_factory=list)
    subcategories: list[str] = Field(default_factory=list)


class UserPreferenceResponseSchema(BaseModel):
    user_id: str
    mode: Literal['wide', 'narrow']
    primary_categories: list[str]
    subcategories: list[str]
    onboarding_completed: bool

    @classmethod
    def from_entity(cls, entity: UserPreference) -> 'UserPreferenceResponseSchema':
        return cls(
            user_id=entity.user_id,
            mode=entity.mode.value,
            primary_categories=entity.primary_categories,
            subcategories=entity.subcategories,
            onboarding_completed=entity.onboarding_completed,
        )


class AuthStartResponseSchema(BaseModel):
    provider: Literal['kakao']
    state: str
    authorization_url: str


class AuthSessionResponseSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'user_id': None,
                    'session_state': 'anonymous',
                    'onboarding_completed': False,
                    'authenticated': False,
                    'auth_provider': 'none',
                    'provider_subject': None,
                },
                {
                    'user_id': 'user-kakao-123',
                    'session_state': 'authenticated',
                    'onboarding_completed': False,
                    'authenticated': True,
                    'auth_provider': 'kakao',
                    'provider_subject': '123456789',
                },
                {
                    'user_id': 'user-kakao-123',
                    'session_state': 'onboarded',
                    'onboarding_completed': True,
                    'authenticated': True,
                    'auth_provider': 'kakao',
                    'provider_subject': '123456789',
                },
            ]
        }
    )

    user_id: str | None
    session_state: Literal['anonymous', 'onboarded', 'authenticated']
    onboarding_completed: bool
    authenticated: bool
    auth_provider: Literal['none', 'demo', 'kakao']
    provider_subject: str | None = None


class AuthLogoutResponseSchema(BaseModel):
    ok: bool


class ArticleCardResponseSchema(BaseModel):
    id: str
    title: str
    summary: str
    primary_category: str
    subcategory: str
    published_at: str
    original_url: HttpUrl
    is_scrapped: bool = False

    @classmethod
    def from_entity(cls, entity: Article, is_scrapped: bool = False) -> 'ArticleCardResponseSchema':
        return cls(
            id=entity.id,
            title=entity.title,
            summary=entity.summary,
            primary_category=entity.primary_category,
            subcategory=entity.subcategory,
            published_at=entity.published_at,
            original_url=entity.original_url,
            is_scrapped=is_scrapped,
        )


class ArticleDetailResponseSchema(ArticleCardResponseSchema):
    content: str

    @classmethod
    def from_entity(cls, entity: Article, service, user_id: str | None = None) -> 'ArticleDetailResponseSchema':
        is_scrapped = False
        if user_id:
            is_scrapped = entity.id in {item.id for item in service.list_scraps(user_id)}
        base = ArticleCardResponseSchema.from_entity(entity, is_scrapped=is_scrapped)
        return cls(**base.model_dump(), content=entity.content)


class FeedBlockResponseSchema(BaseModel):
    key: str
    title: str
    weight: float
    articles: list[ArticleCardResponseSchema]


class FeedResponseSchema(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            'examples': [
                {
                    'user_id': 'user-kakao-123',
                    'mode': 'wide',
                    'blocks': [
                        {
                            'key': 'macro',
                            'title': '거시경제',
                            'weight': 1.0,
                            'articles': [
                                {
                                    'id': 'SUM-001',
                                    'title': '원/달러 환율 변동성 확대',
                                    'summary': '시장 금리와 환율 변동이 커지며 주요 자산 가격이 조정되었습니다.',
                                    'primary_category': 'macro',
                                    'subcategory': 'rates-fx',
                                    'published_at': '2026-04-25',
                                    'original_url': 'https://www.yna.co.kr/view/AKR20260425000000001',
                                    'is_scrapped': False,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )

    user_id: str
    mode: Literal['wide', 'narrow']
    blocks: list[FeedBlockResponseSchema]

    @classmethod
    def from_payload(cls, payload: dict, service, user_id: str) -> 'FeedResponseSchema':
        scrapped_ids = {item.id for item in service.list_scraps(user_id)}
        blocks = []
        for block in payload['blocks']:
            blocks.append(
                FeedBlockResponseSchema(
                    key=block['key'],
                    title=block['title'],
                    weight=block['weight'],
                    articles=[ArticleCardResponseSchema.from_entity(article, article.id in scrapped_ids) for article in block['articles']],
                )
            )
        return cls(user_id=payload['user_id'], mode=payload['mode'], blocks=blocks)


class ScrapToggleResponseSchema(BaseModel):
    user_id: str
    article_id: str
    scrapped: bool


class ScrapListResponseSchema(BaseModel):
    user_id: str
    items: list[ArticleCardResponseSchema]

    @classmethod
    def from_entities(cls, user_id: str, entities: list[Article], service) -> 'ScrapListResponseSchema':
        return cls(user_id=user_id, items=[ArticleCardResponseSchema.from_entity(item, True) for item in entities])


class SummaryArticleInputSchema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

    title: str
    date: str | None = None
    author: str | None = None
    url: HttpUrl | None = None
    content: str


class SummaryRequestSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    article: SummaryArticleInputSchema
    verify: bool = False
    max_retries: int = Field(default=2, ge=0, le=5)
    backend: Literal['codex_exec', 'hermit_http'] = 'codex_exec'
    model: str = 'gpt-5.4-mini'
    reasoning_effort: str = 'low'
    timeout: int = Field(default=300, ge=1, le=600)


class VerificationResponseSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    verdict: Literal['clean', 'suspicious', 'skipped', 'unknown']
    hallucinations: list[str]
    confidence: int = Field(ge=0, le=100)


class ErrorResponseSchema(BaseModel):
    model_config = ConfigDict(extra='forbid')

    code: str
    message: str
    details: str | None = None


class SummaryResponseSchema(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    headline_34: str
    headline_58: str
    headline_89: str
    summary: str
    verify: VerificationResponseSchema = Field(alias='_verify')
    retry_count: int = Field(alias='_retry_count', ge=0)
    violations: list[str] = Field(alias='_violations', default_factory=list)
    headline_34_len: int = Field(alias='_headline_34_len', ge=0)
    headline_58_len: int = Field(alias='_headline_58_len', ge=0)
    headline_89_len: int = Field(alias='_headline_89_len', ge=0)

    @field_validator('headline_34')
    @classmethod
    def validate_headline_34(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS['headline_34']
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f'headline_34 must be {min_len}~{max_len} chars')
        return value

    @field_validator('headline_58')
    @classmethod
    def validate_headline_58(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS['headline_58']
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f'headline_58 must be {min_len}~{max_len} chars')
        return value

    @field_validator('headline_89')
    @classmethod
    def validate_headline_89(cls, value: str) -> str:
        value = normalize_text(value)
        min_len, max_len = HEADLINE_LIMITS['headline_89']
        if not (min_len <= len(value) <= max_len):
            raise ValueError(f'headline_89 must be {min_len}~{max_len} chars')
        return value
