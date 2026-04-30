from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

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


class ArticleClassificationDecision(BaseModel):
    keep: bool
    primary_category: str | None = None
    subcategory: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ''


class ArticleClassifier(Protocol):
    def __call__(
        self,
        *,
        article_id: str,
        title: str,
        summary: str,
        content: str,
        original_url: str,
        raw_primary: str,
        raw_subcategory: str,
    ) -> ArticleClassificationDecision | None: ...


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

SOURCE_CATEGORIES_REQUIRING_ECONOMIC_TITLE_SIGNAL = {'정치', '사회', '문화연예', '연예', '스포츠', '생활', '종합'}
RELIABLE_SOURCE_CATEGORY_BY_SUBCATEGORY = {
    '증권': ('assets', 'domestic-stocks'),
    '주식시장': ('assets', 'domestic-stocks'),
    '국제경제': ('macro', 'rates-fx'),
    '금융': ('macro', 'rates-fx'),
    '에너지': ('macro', 'energy'),
    '무역': ('macro', 'supply-chain'),
    '자동차': ('sectors', 'mobility'),
    '반도체': ('sectors', 'semiconductor'),
    '산업정책': ('policy', 'regulation'),
}
ECONOMIC_TITLE_SIGNAL_PATTERN = re.compile(
    r'증시|코스피|코스닥|주가|증권|상장|지분|투자|환율|달러|금리|국채|물가|인플레|원유|유가|에너지|수출|수입|무역|공급망|관세|바이어|전시회|반도체|배터리|전기차|자동차|조선|원전|부동산|주택|아파트|분양|청약|기업|산업|부두|항만|물류'
)

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


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding='utf-8')


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


def _score_index(data_dir: Path) -> dict[str, dict]:
    scored_dir = data_dir / 'scored'
    if not scored_dir.exists():
        return {}

    scored: dict[str, dict] = {}
    for path in sorted(scored_dir.glob('*.json')):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            continue
        article_id = str(payload.get('_article_id') or path.stem).strip()
        if article_id:
            scored[article_id] = payload
    return scored


def _score_weight(score_payload: dict) -> float:
    raw_score = score_payload.get('score')
    if not isinstance(raw_score, int | float):
        return 1.0
    bounded_score = max(0.0, min(float(raw_score), 100.0))
    return round(bounded_score / 100.0, 4)


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


def _has_economic_title_signal(title: str) -> bool:
    return bool(ECONOMIC_TITLE_SIGNAL_PATTERN.search(title))


def _is_supported_pair(primary: str | None, subcategory: str | None) -> bool:
    if not primary or not subcategory:
        return False
    return subcategory in SUPPORTED_SUBCATEGORIES.get(primary, set())


def _classifier_cache_path(data_dir: Path) -> Path:
    return data_dir / 'classification_cache.json'


def _classifier_cache_key(*, article_id: str, title: str, summary: str, content: str, original_url: str) -> str:
    digest = hashlib.sha256(f'{article_id}\n{original_url}\n{title}\n{summary}\n{content}'.encode('utf-8')).hexdigest()
    return digest


def _load_classifier_cache(data_dir: Path) -> dict[str, dict]:
    path = _classifier_cache_path(data_dir)
    if not path.exists():
        return {}
    payload = _read_json(path)
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def _store_classifier_cache(data_dir: Path, cache: dict[str, dict]) -> None:
    _write_json(_classifier_cache_path(data_dir), cache)


def _maybe_classify_with_fallback(
    *,
    data_dir: Path,
    classifier: ArticleClassifier | None,
    classifier_cache: dict[str, dict],
    article_id: str,
    title: str,
    summary: str,
    content: str,
    original_url: str,
    raw_primary: str,
    raw_subcategory: str,
    min_confidence: float,
) -> tuple[str, str] | None:
    if classifier is None:
        return None

    cache_key = _classifier_cache_key(
        article_id=article_id,
        title=title,
        summary=summary,
        content=content,
        original_url=original_url,
    )
    cached_payload = classifier_cache.get(cache_key)
    if cached_payload is not None:
        decision = ArticleClassificationDecision.model_validate(cached_payload)
    else:
        decision = classifier(
            article_id=article_id,
            title=title,
            summary=summary,
            content=content,
            original_url=original_url,
            raw_primary=raw_primary,
            raw_subcategory=raw_subcategory,
        )
        if decision is None:
            return None
        classifier_cache[cache_key] = decision.model_dump()
        _store_classifier_cache(data_dir, classifier_cache)

    if not decision.keep or decision.confidence < min_confidence:
        return None
    if not _is_supported_pair(decision.primary_category, decision.subcategory):
        return None
    return decision.primary_category, decision.subcategory


def _derive_categories(
    article_payload: dict,
    category_payload: dict,
    *,
    data_dir: Path,
    classifier: ArticleClassifier | None,
    classifier_cache: dict[str, dict],
    article_id: str,
    summary: str,
    original_url: str,
    min_confidence: float,
) -> tuple[str, str] | None:
    title = str(article_payload.get('title') or '')
    content = str(article_payload.get('content') or '')
    raw_primary = str(category_payload.get('primary_category') or '')
    raw_subcategory = str(category_payload.get('subcategory') or '')

    if raw_primary in SOURCE_CATEGORIES_REQUIRING_ECONOMIC_TITLE_SIGNAL and not _has_economic_title_signal(title):
        return None

    primary = _normalise_primary(raw_primary)
    subcategory = _normalise_subcategory(raw_subcategory, primary)
    if primary not in SUPPORTED_SUBCATEGORIES:
        return None

    reliable_pair = RELIABLE_SOURCE_CATEGORY_BY_SUBCATEGORY.get(raw_subcategory)
    if reliable_pair:
        return reliable_pair

    classified = _classify_from_keywords(title, content)
    if classified:
        return classified

    return _maybe_classify_with_fallback(
        data_dir=data_dir,
        classifier=classifier,
        classifier_cache=classifier_cache,
        article_id=article_id,
        title=title,
        summary=summary,
        content=content,
        original_url=original_url,
        raw_primary=raw_primary,
        raw_subcategory=raw_subcategory,
        min_confidence=min_confidence,
    )


def load_summarized_articles(
    data_dir: Path,
    *,
    classifier: ArticleClassifier | None = None,
    classifier_min_confidence: float = 0.75,
) -> list[ArticleIngestRow]:
    json_dir = data_dir / 'json'
    summarized_dir = data_dir / 'summarized'
    verified_dir = data_dir / 'verified'
    if not json_dir.exists() or not summarized_dir.exists() or not verified_dir.exists():
        return []

    categories = _category_index(data_dir)
    scores = _score_index(data_dir)
    classifier_cache = _load_classifier_cache(data_dir)
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
        derived = _derive_categories(
            article_payload,
            category_payload,
            data_dir=data_dir,
            classifier=classifier,
            classifier_cache=classifier_cache,
            article_id=article_id,
            summary=summary,
            original_url=original_url,
            min_confidence=classifier_min_confidence,
        )
        if derived is None:
            continue
        primary, subcategory = derived
        score_weight = _score_weight(scores.get(article_id, {}))
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
                score_weight=score_weight,
            )
        )
    return rows
