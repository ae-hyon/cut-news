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


class ArticleDerivedCategory(BaseModel):
    primary_category: str
    subcategory: str


PRIMARY_CATEGORY_ALIASES = {
    '경제': 'economy',
    '정치': 'politics',
    '사회': 'politics',
    '국제': 'global',
    '산업': 'tech',
    'IT': 'tech',
    'IT통신': 'tech',
    '테크': 'tech',
    '문화연예': 'entertainment',
    '연예': 'entertainment',
    '스포츠': 'sports',
    '생활': 'lifestyle',
    '종합': 'economy',
}

SUBCATEGORY_ALIASES = {
    '증권': 'stock-domestic',
    '주식시장': 'stock-domestic',
    '국제경제': 'economy-finance',
    '금융': 'economy-finance',
    '에너지': 'economy-trade',
    '무역': 'economy-trade',
    '자동차': 'tech-bigtech',
    '반도체': 'tech-semiconductor',
    'IT통신': 'tech-bigtech',
    '산업정책': 'politics-policy',
    '대통령실': 'politics-domestic',
    '청와대': 'politics-domestic',
    '교육정책': 'politics-policy',
}

DEFAULT_SUBCATEGORY_BY_PRIMARY = {
    'stock': 'stock-domestic',
    'crypto': 'crypto-bitcoin',
    'realestate': 'realestate-apt',
    'politics': 'politics-domestic',
    'economy': 'economy-macro',
    'tech': 'tech-ai',
    'entertainment': 'entertainment-kpop',
    'sports': 'sports-soccer',
    'global': 'global-us',
    'lifestyle': 'lifestyle-health',
}

SUPPORTED_SUBCATEGORIES = {
    'stock': {'stock-domestic', 'stock-overseas', 'stock-etf', 'stock-unlisted'},
    'crypto': {'crypto-bitcoin', 'crypto-altcoin', 'crypto-defi', 'crypto-nft'},
    'realestate': {'realestate-apt', 'realestate-subscription', 'realestate-lease', 'realestate-commercial'},
    'politics': {'politics-domestic', 'politics-diplomacy', 'politics-policy'},
    'economy': {'economy-macro', 'economy-finance', 'economy-trade'},
    'tech': {'tech-ai', 'tech-semiconductor', 'tech-startup', 'tech-bigtech'},
    'entertainment': {'entertainment-kpop', 'entertainment-drama', 'entertainment-movie'},
    'sports': {'sports-soccer', 'sports-baseball', 'sports-basketball', 'sports-esports'},
    'global': {'global-us', 'global-china', 'global-europe', 'global-asia'},
    'lifestyle': {'lifestyle-health', 'lifestyle-travel', 'lifestyle-food'},
}

SOURCE_CATEGORIES_REQUIRING_ECONOMIC_TITLE_SIGNAL = {'정치', '사회', '문화연예', '연예', '스포츠', '생활', '종합'}
MIN_VERIFICATION_CONFIDENCE = 80
MIN_DESCRIPTION_SOURCE_VERIFICATION_CONFIDENCE = 90
MAX_SUMMARY_RETRY_COUNT = 2
RELIABLE_SOURCE_CATEGORY_BY_SUBCATEGORY = {
    '증권': ('stock', 'stock-domestic'),
    '주식시장': ('stock', 'stock-domestic'),
    '국제경제': ('economy', 'economy-finance'),
    '금융': ('economy', 'economy-finance'),
    '에너지': ('economy', 'economy-trade'),
    '무역': ('economy', 'economy-trade'),
    '자동차': ('tech', 'tech-bigtech'),
    '반도체': ('tech', 'tech-semiconductor'),
    '산업정책': ('politics', 'politics-policy'),
}
ECONOMIC_TITLE_SIGNAL_PATTERN = re.compile(
    r'증시|코스피|코스닥|주가|증권|상장|지분|투자|환율|달러|금리|국채|물가|인플레|원유|유가|에너지|수출|수입|무역|공급망|관세|바이어|전시회|반도체|배터리|전기차|자동차|조선|원전|부동산|주택|아파트|분양|청약|기업|산업|부두|항만|물류'
)

KEYWORD_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ('stock', 'stock-domestic', ('증권', '증시', '코스피', '코스닥', '주가', '투자증권', '상장', '지분 매각')),
    ('stock', 'stock-overseas', ('s&p', '나스닥', '다우', '미 증시', '미국 증시', '해외주식')),
    ('stock', 'stock-etf', ('etf', '상장지수펀드')),
    ('crypto', 'crypto-bitcoin', ('비트코인', 'bitcoin', 'btc')),
    ('crypto', 'crypto-altcoin', ('이더리움', '알트코인', 'ethereum', 'eth')),
    ('realestate', 'realestate-lease', ('전세', '월세', '임대차')),
    ('realestate', 'realestate-subscription', ('청약', '분양')),
    ('realestate', 'realestate-apt', ('부동산', '아파트', '주택')),
    ('economy', 'economy-trade', ('원유', '유가', '정유', '에너지', '무역', '수출', '수입', '공급망', '관세', 'opec')),
    ('economy', 'economy-finance', ('환율', '달러-원', '달러원', '금리', '국채', '물가', '인플레', 'cpi', 'fomc', '금융')),
    ('economy', 'economy-macro', ('gdp', '성장률', '거시', '경기')),
    ('politics', 'politics-policy', ('정부', '기재부', '예산', '추경', '세제', '세금', '재정', '규제', '법안', '정책')),
    ('politics', 'politics-domestic', ('국회', '대통령', '정당', '청와대')),
    ('politics', 'politics-diplomacy', ('외교', '정상회담', '안보')),
    ('tech', 'tech-semiconductor', ('반도체', '메모리', '파운드리', '리노공업', 'sk하이닉스', '삼성전자')),
    ('tech', 'tech-bigtech', ('현대차', '기아', '배터리', '전기차', '모빌리티', '자동차', '빅테크')),
    ('tech', 'tech-ai', ('ai', '인공지능')),
    ('tech', 'tech-startup', ('스타트업', '창업', '벤처')),
    ('entertainment', 'entertainment-kpop', ('k-pop', 'kpop', '아이돌')),
    ('entertainment', 'entertainment-drama', ('드라마', 'ott')),
    ('entertainment', 'entertainment-movie', ('영화', '개봉')),
    ('sports', 'sports-soccer', ('축구', '월드컵')),
    ('sports', 'sports-baseball', ('야구', 'kbo', 'mlb')),
    ('sports', 'sports-basketball', ('농구', 'nba', 'kbl')),
    ('global', 'global-us', ('미국', '워싱턴')),
    ('global', 'global-china', ('중국', '베이징')),
    ('global', 'global-europe', ('eu', '유럽')),
    ('lifestyle', 'lifestyle-health', ('건강', '헬스케어', '웰니스')),
    ('lifestyle', 'lifestyle-travel', ('여행', '항공')),
    ('lifestyle', 'lifestyle-food', ('맛집', '식음료')),
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


def _quality_gate_failure_reason(article_payload: dict, summary_payload: dict, verification_payload: dict) -> str | None:
    verdict = str(verification_payload.get('verdict') or '').strip().lower()
    if verdict != 'clean':
        return 'verdict_not_clean'

    confidence = verification_payload.get('confidence')
    if not isinstance(confidence, int | float):
        confidence = 100
    min_confidence = MIN_VERIFICATION_CONFIDENCE
    if str(article_payload.get('content_source') or '').strip().lower() == 'description':
        min_confidence = MIN_DESCRIPTION_SOURCE_VERIFICATION_CONFIDENCE
    if float(confidence) < min_confidence:
        if min_confidence == MIN_DESCRIPTION_SOURCE_VERIFICATION_CONFIDENCE:
            return 'description_low_confidence'
        return 'low_confidence'

    violations = summary_payload.get('_violations')
    if isinstance(violations, list) and any(str(item).strip() for item in violations):
        return 'violations'

    retry_count = summary_payload.get('_retry_count')
    if isinstance(retry_count, int | float) and int(retry_count) > MAX_SUMMARY_RETRY_COUNT:
        return 'too_many_retries'
    return None


def _classify_from_keywords(title: str, content: str) -> tuple[str, str] | None:
    haystack = f'{title} {content}'.lower()
    for primary, subcategory, keywords in KEYWORD_RULES:
        if any(keyword.lower() in haystack for keyword in keywords):
            return primary, subcategory
    return None


def _has_economic_title_signal(title: str) -> bool:
    return bool(ECONOMIC_TITLE_SIGNAL_PATTERN.search(title))


def _derive_categories(article_payload: dict, category_payload: dict) -> ArticleDerivedCategory | None:
    title = str(article_payload.get('title') or '')
    content = str(article_payload.get('content') or '')
    raw_primary = str(category_payload.get('primary_category') or '')
    raw_subcategory = str(category_payload.get('subcategory') or '')

    if raw_primary in SOURCE_CATEGORIES_REQUIRING_ECONOMIC_TITLE_SIGNAL and not _has_economic_title_signal(title):
        return None

    primary = _normalise_primary(raw_primary)
    if primary not in SUPPORTED_SUBCATEGORIES:
        return None

    reliable_pair = RELIABLE_SOURCE_CATEGORY_BY_SUBCATEGORY.get(raw_subcategory)
    if reliable_pair:
        return ArticleDerivedCategory(primary_category=reliable_pair[0], subcategory=reliable_pair[1])

    classified = _classify_from_keywords(title, content)
    if classified:
        return ArticleDerivedCategory(primary_category=classified[0], subcategory=classified[1])

    return None


def _increment(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def load_summarized_articles_report(data_dir: Path) -> tuple[list[ArticleIngestRow], dict[str, dict[str, int]]]:
    json_dir = data_dir / 'json'
    summarized_dir = data_dir / 'summarized'
    verified_dir = data_dir / 'verified'
    empty_report = {
        'quality_gate_skip_counts': {},
    }
    if not json_dir.exists() or not summarized_dir.exists() or not verified_dir.exists():
        return [], empty_report

    categories = _category_index(data_dir)
    scores = _score_index(data_dir)
    rows: list[ArticleIngestRow] = []
    quality_gate_skip_counts: dict[str, int] = {}
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
        quality_gate_reason = _quality_gate_failure_reason(article_payload, summary_payload, verification_payload)
        if quality_gate_reason is not None:
            _increment(quality_gate_skip_counts, quality_gate_reason)
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
        )
        if derived is None:
            continue
        score_weight = _score_weight(scores.get(article_id, {}))
        rows.append(
            ArticleIngestRow(
                id=f'SUM-{article_id}',
                title=title,
                summary=summary,
                content=content,
                primary_category=derived.primary_category,
                subcategory=derived.subcategory,
                published_at=published_at,
                original_url=original_url,
                score_weight=score_weight,
            )
        )
    return rows, {
        'quality_gate_skip_counts': quality_gate_skip_counts,
    }


def load_summarized_articles(data_dir: Path) -> list[ArticleIngestRow]:
    rows, _report = load_summarized_articles_report(data_dir)
    return rows
