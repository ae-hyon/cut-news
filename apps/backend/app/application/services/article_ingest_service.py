from __future__ import annotations

import json
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
    '경제': 'economy',
    '정치': 'politics',
    '문화연예': 'entertainment',
    '연예': 'entertainment',
    '스포츠': 'sports',
    'IT': 'tech',
    'IT통신': 'tech',
    '테크': 'tech',
    '국제': 'politics',
    '사회': 'politics',
    '생활': 'entertainment',
    '종합': 'politics',
}

SUBCATEGORY_ALIASES = {
    '증권': 'stocks',
    '주식시장': 'stocks',
    '금융': 'macro',
    '에너지': 'macro',
    '무역': 'macro',
    '국제경제': 'macro',
    '자동차': 'macro',
    '부동산': 'real-estate',
    '청와대': 'policy',
    '대통령실': 'policy',
    '산업정책': 'policy',
    '교육정책': 'policy',
    '지방선거': 'assembly',
    '정당': 'assembly',
    '국방': 'diplomacy',
    '외교안보': 'diplomacy',
    '해외사건': 'diplomacy',
    '방송': 'broadcast',
    '해외방송': 'broadcast',
    '영화': 'film',
    '가요': 'music',
    '축구': 'soccer',
    '야구': 'baseball',
    'e스포츠': 'esports',
    'IT통신': 'ai',
}

DEFAULT_SUBCATEGORY_BY_PRIMARY = {
    'economy': 'macro',
    'politics': 'policy',
    'entertainment': 'broadcast',
    'tech': 'ai',
    'sports': 'soccer',
}

SUPPORTED_SUBCATEGORIES = {
    'economy': {'stocks', 'real-estate', 'macro'},
    'politics': {'policy', 'assembly', 'diplomacy'},
    'entertainment': {'broadcast', 'music', 'film'},
    'tech': {'ai', 'startup', 'semiconductor'},
    'sports': {'soccer', 'baseball', 'esports'},
}


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding='utf-8'))


def _normalise_primary(raw: str | None) -> str:
    return PRIMARY_CATEGORY_ALIASES.get(raw or '', raw or 'politics')


def _normalise_subcategory(raw: str | None, primary: str) -> str:
    subcategory = SUBCATEGORY_ALIASES.get(raw or '', DEFAULT_SUBCATEGORY_BY_PRIMARY.get(primary, 'policy'))
    if subcategory not in SUPPORTED_SUBCATEGORIES.get(primary, set()):
        return DEFAULT_SUBCATEGORY_BY_PRIMARY.get(primary, 'policy')
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


def load_summarized_articles(data_dir: Path) -> list[ArticleIngestRow]:
    json_dir = data_dir / 'json'
    summarized_dir = data_dir / 'summarized'
    if not json_dir.exists() or not summarized_dir.exists():
        return []

    categories = _category_index(data_dir)
    rows: list[ArticleIngestRow] = []
    for article_path in sorted(json_dir.glob('*.json')):
        article_id = article_path.stem
        summary_path = summarized_dir / f'{article_id}.json'
        if not summary_path.exists():
            continue

        article_payload = _read_json(article_path)
        summary_payload = _read_json(summary_path)
        if not isinstance(article_payload, dict) or not isinstance(summary_payload, dict):
            continue

        summary = str(summary_payload.get('summary') or '').strip()
        title = _title(summary_payload, article_payload)
        content = str(article_payload.get('content') or '').strip()
        original_url = str(article_payload.get('url') or '').strip()
        published_at = _published_at(article_payload)
        if not (summary and title and content and original_url and published_at):
            continue

        category_payload = categories.get(article_id, {})
        primary = _normalise_primary(category_payload.get('primary_category'))
        subcategory = _normalise_subcategory(category_payload.get('subcategory'), primary)
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
