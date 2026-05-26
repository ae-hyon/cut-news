from __future__ import annotations

import json
from pathlib import Path

from crawler.export_raw import export_articles_to_raw, load_articles_from_json
from crawler.pipeline import save_raw_articles


def test_load_articles_from_json_accepts_legacy_korean_crawler_output(tmp_path: Path):
    path = tmp_path / 'articles.json'
    path.write_text(
        json.dumps(
            [
                {
                    '제목': '네이버 API로 수집한 사회 뉴스',
                    '날짜': '2026-04-28 10:00',
                    '본문': '사회 뉴스 본문입니다. summarizer로 넘길 실제 본문입니다.',
                    '링크': 'https://news.example.com/society/1',
                }
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    articles = load_articles_from_json(path)

    assert len(articles) == 1
    assert articles[0].title == '네이버 API로 수집한 사회 뉴스'
    assert articles[0].date == '2026-04-28 10:00'
    assert str(articles[0].url) == 'https://news.example.com/society/1'
    assert articles[0].content.startswith('사회 뉴스 본문')


def test_load_articles_from_json_preserves_crawler_category_metadata(tmp_path: Path):
    path = tmp_path / 'articles.json'
    path.write_text(
        json.dumps(
            [
                {
                    'article_id': 'naver-1',
                    'title': '카테고리 메타데이터 기사',
                    'date': '2026-05-26',
                    'url': 'https://news.example.com/stock/1',
                    'content': '주식시장 기사 본문입니다.',
                    'content_source': 'body',
                    'source_category': 'stock',
                    'source_query': '코스피',
                }
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    articles = load_articles_from_json(path)
    raw_dir = tmp_path / 'raw'
    paths = save_raw_articles(articles, raw_dir)

    assert articles[0].source_category == 'stock'
    assert articles[0].source_query == '코스피'
    raw_text = paths[0].read_text(encoding='utf-8')
    assert '콘텐츠소스: body' in raw_text
    assert '소스카테고리: stock' in raw_text
    assert '소스쿼리: 코스피' in raw_text


def test_exported_legacy_crawler_output_can_be_saved_as_summarizer_raw(tmp_path: Path):
    input_path = tmp_path / 'articles.json'
    raw_dir = tmp_path / 'raw'
    input_path.write_text(
        json.dumps(
            [
                {
                    'title': '영문 키 기반 crawler 결과',
                    'date': '2026-04-28',
                    'author': '박기자',
                    'url': 'https://news.example.com/economy/1',
                    'content': '경제 뉴스 본문입니다. 충분한 본문을 summarizer raw 계약으로 저장합니다.',
                }
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    paths = save_raw_articles(load_articles_from_json(input_path), raw_dir)

    assert paths == [raw_dir / 'raw-001.txt']
    assert '제목: 영문 키 기반 crawler 결과' in paths[0].read_text(encoding='utf-8')
    assert 'URL: https://news.example.com/economy/1' in paths[0].read_text(encoding='utf-8')


def test_export_articles_to_raw_clears_stale_raw_files_before_writing_latest_dataset(tmp_path: Path):
    input_path = tmp_path / 'articles.json'
    raw_dir = tmp_path / 'raw'
    raw_dir.mkdir()
    stale_path = raw_dir / '999.txt'
    stale_path.write_text('stale', encoding='utf-8')
    input_path.write_text(
        json.dumps(
            [
                {
                    'title': '새 기사',
                    'url': 'https://news.example.com/new/1',
                    'content': '새 기사 본문입니다.',
                }
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    paths = export_articles_to_raw(input_path, raw_dir, clear=True)

    assert paths == [raw_dir / 'raw-001.txt']
    assert not stale_path.exists()
    assert '제목: 새 기사' in paths[0].read_text(encoding='utf-8')


def test_export_articles_to_raw_can_clear_downstream_summarizer_outputs_for_fresh_pipeline_run(tmp_path: Path):
    input_path = tmp_path / 'articles.json'
    raw_dir = tmp_path / 'raw'
    derived_dir = tmp_path / 'summarized'
    raw_dir.mkdir()
    derived_dir.mkdir()
    (derived_dir / '001.json').write_text('{"stale": true}', encoding='utf-8')
    nested_dir = derived_dir / 'nested'
    nested_dir.mkdir()
    (nested_dir / 'keep.txt').write_text('stale nested', encoding='utf-8')
    input_path.write_text(
        json.dumps(
            [
                {
                    'title': '새 기사',
                    'url': 'https://news.example.com/new/1',
                    'content': '새 기사 본문입니다.',
                }
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    paths = export_articles_to_raw(input_path, raw_dir, clear=True, clear_derived_dirs=[derived_dir])

    assert paths == [raw_dir / 'raw-001.txt']
    assert list(derived_dir.iterdir()) == []


def test_export_articles_to_raw_can_limit_latest_dataset_for_bounded_pipeline_smoke(tmp_path: Path):
    input_path = tmp_path / 'articles.json'
    raw_dir = tmp_path / 'raw'
    input_path.write_text(
        json.dumps(
            [
                {
                    'article_id': 'a1',
                    'title': '첫 기사',
                    'url': 'https://news.example.com/1',
                    'content': '본문 1',
                },
                {
                    'article_id': 'a2',
                    'title': '둘 기사',
                    'url': 'https://news.example.com/2',
                    'content': '본문 2',
                },
                {
                    'article_id': 'a3',
                    'title': '셋 기사',
                    'url': 'https://news.example.com/3',
                    'content': '본문 3',
                },
            ],
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )

    paths = export_articles_to_raw(input_path, raw_dir, max_articles=2)

    assert paths == [raw_dir / 'a1.txt', raw_dir / 'a2.txt']
    assert sorted(path.name for path in raw_dir.iterdir()) == ['a1.txt', 'a2.txt']
    assert '첫 기사' in (raw_dir / 'a1.txt').read_text(encoding='utf-8')
