from __future__ import annotations

import json
from pathlib import Path

from crawler.export_raw import load_articles_from_json
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

    assert paths == [raw_dir / '001.txt']
    assert '제목: 영문 키 기반 crawler 결과' in paths[0].read_text(encoding='utf-8')
    assert 'URL: https://news.example.com/economy/1' in paths[0].read_text(encoding='utf-8')
