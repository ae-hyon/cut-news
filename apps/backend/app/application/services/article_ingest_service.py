from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ArticleIngestRow(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    content: str = Field(min_length=1)
    primary_category: str = Field(min_length=1)
    subcategory: str = Field(min_length=1)
    published_at: str = Field(min_length=1)
    original_url: str = Field(min_length=1)
    score_weight: float = 1.0


PRIMARY_CATEGORY_ALIASES = {
    '경제': 'assets',
    '정치': 'policy',
    '사회': 'policy',
    '국제': 'macro',
    '산업': 'sectors',
    'IT': 'sectors',
    'IT통신': 'sectors',
    '테크': 'sectors',
    '문화연예': 'sectors',
    '연예': 'sectors',
    '생활': 'macro',
    '종합': 'macro',
}

SUBCATEGORY_ALIASES = {
    '증권': 'domestic-stocks',
    '주식시장': 'domestic-stocks',
    '국제경제': 'rates-fx',
    '금융': 'rates-fx',
    '에너지': 'energy',
    '무역': 'supply-chain',
    '자동차': 'mobility',
    '반도체': 'semiconductor',
    'IT통신': 'semiconductor',
    '산업정책': 'regulation',
    '대통령실': 'fiscal',
    '청와대': 'fiscal',
    '교육정책': 'regulation',
}

DEFAULT_SUBCATEGORY_BY_PRIMARY = {
    'sectors': 'semiconductor',
    'macro': 'rates-fx',
    'assets': 'domestic-stocks',
    'policy': 'regulation',
}

SUPPORTED_SUBCATEGORIES = {
    'sectors': {'semiconductor', 'mobility', 'bio'},
    'macro': {'rates-fx', 'energy', 'supply-chain'},
    'assets': {'domestic-stocks', 'global-stocks', 'real-estate'},
    'policy': {'fiscal', 'central-bank', 'regulation'},
}

KEYWORD_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ('assets', 'domestic-stocks', ('증권', '증시', '코스피', '코스닥', '주가', '투자증권', '상장', '지분 매각')),
    ('assets', 'real-estate', ('부동산', '전세', '아파트', '분양', '주택', '청약')),
    ('assets', 'global-stocks', ('s&p', '나스닥', '다우', '미 증시', '미국 증시', '해외주식')),
    ('macro', 'energy', ('원유', '유가', '정유', '에너지', '가스', '배럴', 'opec')),
    ('macro', 'rates-fx', ('환율', '달러-원', '달러원', '금리', '국채', '물가', '인플레', 'cpi', 'fomc')),
    ('policy', 'central-bank', ('한국은행', '연준', '기준금리', '통화정책', '금통위', 'fed')),
    ('policy', 'fiscal', ('정부', '기재부', '예산', '추경', '세제', '세금', '재정')),
    ('policy', 'regulation', ('금융위', '금감원', '규제', '법안', '공시', '감독', '제도')),
    ('sectors', 'semiconductor', ('반도체', '메모리', '파운드리', '리노공업', 'sk하이닉스', '삼성전자')),
    ('sectors', 'mobility', ('현대차', '기아', '배터리', '전기차', '모빌리티', '자동차')),
    ('sectors', 'bio', ('바이오', '제약', '의료기기', '임상', '헬스케어')),
)


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding='utf-8'))


def _normalise_primary(raw: str | None) -> str:
    return PRIMARY_CATEGORY_ALIASES.get(raw or '', raw or 'macro')


def _normalise_subcategory(raw: str | None, primary: str) -> str:
    subcategory = SUBCATEGORY_ALIASES.get(raw or '', DEFAULT_SUBCATEGORY_BY_PRIMARY.get(primary, 'regulation'))
    if subcategory not in SUPPORTED_SUBCATEGORIES.get(primary, set()):
        return DEFAULT_SUBCATEGORY_BY_PRIMARY.get(primary, 'regulation')
    return subcategory


def _category_index(data_dir: Path) -> dict[str, dict]:
    path = data_dir / 'category_map.json'
    if not path.exists():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, list):
        return {}
    return {str(item.get('article_id')): item for item in payload if isinstance(item, dict) and item.get('article_id')}


def _title(summary_payload: dict, article_payload: dict) -> str:
    return str(summary_payload.get('headline_34') or summary_payload.get('_title') or article_payload.get('title') or '').strip()


def _published_at(article_payload: dict) -> str:
    return str(article_payload.get('date') or '').strip()[:10]


def _classify_from_keywords(title: str, content: str) -> tuple[str, str] | None:
    haystack = f'{title} {content}'.lower()
    for primary, subcategory, keywords in KEYWORD_RULES:
        if any(keyword.lower() in haystack for keyword in keywords):
            return primary, subcategory
    return None


def _derive_categories(article_payload: dict, category_payload: dict) -> tuple[str, str] | None:
    title = str(article_payload.get('title') or '')
    content = str(article_payload.get('content') or '')
    classified = _classify_from_keywords(title, content)
    if classified:
        return classified

    primary = _normalise_primary(category_payload.get('primary_category'))
    subcategory = _normalise_subcategory(category_payload.get('subcategory'), primary)
    if primary not in SUPPORTED_SUBCATEGORIES:
        return None

    if primary == 'policy' and re.search(r'증권|증시|상장|주가|환율|금리|원유|유가|반도체|자동차|부동산', f'{title} {content}'):
        classified = _classify_from_keywords(title, content)
        if classified:
            return classified
    return primary, subcategory


def load_summarized_articles(data_dir: Path) -> list[ArticleIngestRow]:
    json_dir = data_dir / 'json'
    summarized_dir = data_dir / 'summarized'
    verified_dir = data_dir / 'verified'
    if not json_dir.exists() or not summarized_dir.exists() or not verified_dir.exists():
        return []

    categories = _category_index(data_dir)
    rows: list[ArticleIngestRow] = []
    for article_path in sorted(json_dir.glob('*.json')):
        article_id = article_path.stem
        summary_path = summarized_dir / f'{article_id}.json'
        verification_path = verified_dir / f'{article_id}.json'
        if not summary_path.exists() or not verification_path.exists():
            continue

        article_payload = _read_json(article_path)
        summary_payload = _read_json(summary_path)
        verification_payload = _read_json(verification_path)
        if not isinstance(article_payload, dict) or not isinstance(summary_payload, dict) or not isinstance(verification_payload, dict):
            continue
        if str(verification_payload.get('verdict') or '').strip().lower() != 'clean':
            continue

        summary = str(summary_payload.get('summary') or '').strip()
        title = _title(summary_payload, article_payload)
        content = str(article_payload.get('content') or '').strip()
        original_url = str(article_payload.get('url') or '').strip()
        published_at = _published_at(article_payload)
        if not (summary and title and content and original_url and published_at):
            continue

        category_payload = categories.get(article_id, {})
        derived = _derive_categories(article_payload, category_payload)
        if derived is None:
            continue
        primary, subcategory = derived
        rows.append(
            ArticleIngestRow(
                id=f'SUM-{article_id}',
                title=title,
                summary=summary,
                content=content,
                primary_category=primary,
                subcategory=subcategory,
                published_at=published_at,
                original_url=original_url,
                score_weight=1.0,
            )
        )
    return rows
