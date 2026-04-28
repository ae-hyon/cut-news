from __future__ import annotations

import json
from pathlib import Path

from app.application.services.article_ingest_service import load_summarized_articles


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def test_load_summarized_articles_builds_backend_article_rows_from_summarizer_outputs(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {
            'title': '시장 금리 하락에 증권주 강세',
            'date': '2026-04-28',
            'author': '김기자',
            'url': 'https://example.com/economy/1',
            'content': '시장 금리가 하락하면서 증권주가 강세를 보였다는 본문입니다.',
        },
    )
    write_json(
        dataset / 'summarized' / '001.json',
        {
            'headline_34': '시장 금리 하락에 증권주 강세',
            'headline_58': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였다',
            'headline_89': '시장 금리가 하락하면서 증권주가 일제히 강세를 보였고 투자자들은 정책 변화를 주시하고 있다',
            'summary': '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.',
        },
    )
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    rows = load_summarized_articles(dataset)

    assert len(rows) == 1
    assert rows[0].id == 'SUM-001'
    assert rows[0].title == '시장 금리 하락에 증권주 강세'
    assert rows[0].summary == '시장 금리 하락 영향으로 증권주가 강세를 보였습니다.'
    assert rows[0].content.startswith('시장 금리가 하락하면서')
    assert rows[0].primary_category == 'economy'
    assert rows[0].subcategory == 'stocks'
    assert rows[0].published_at == '2026-04-28'
    assert rows[0].original_url == 'https://example.com/economy/1'
    assert rows[0].score_weight == 1.0


def test_load_summarized_articles_skips_items_without_summary(tmp_path: Path):
    dataset = tmp_path
    write_json(
        dataset / 'json' / '001.json',
        {'title': '제목', 'date': '2026-04-28', 'url': 'https://example.com/1', 'content': '본문'},
    )
    write_json(dataset / 'category_map.json', [{'article_id': '001', 'primary_category': '경제', 'subcategory': '증권'}])

    assert load_summarized_articles(dataset) == []


def test_repo_summarizer_dataset_maps_to_supported_backend_categories():
    rows = load_summarized_articles(Path(__file__).resolve().parents[2] / 'summarizer' / 'data')

    assert len(rows) >= 1
    supported = {
        'economy': {'stocks', 'real-estate', 'macro'},
        'politics': {'policy', 'assembly', 'diplomacy'},
        'entertainment': {'broadcast', 'music', 'film'},
        'tech': {'ai', 'startup', 'semiconductor'},
        'sports': {'soccer', 'baseball', 'esports'},
    }
    for row in rows:
        assert row.primary_category in supported
        assert row.subcategory in supported[row.primary_category]
