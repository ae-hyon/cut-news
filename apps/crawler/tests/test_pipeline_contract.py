from __future__ import annotations

from pathlib import Path

from crawler.pipeline import save_raw_articles
from crawler.schemas import CrawledArticle


def test_save_raw_articles_writes_summarizer_step1_raw_contract(tmp_path: Path):
    articles = [
        CrawledArticle(
            title='수집된 뉴스 제목',
            date='2026-04-28',
            author='홍길동',
            url='https://news.example.com/1',
            content='수집된 뉴스 본문입니다. 충분한 본문을 그대로 전달합니다.',
            media='연합뉴스',
        )
    ]

    paths = save_raw_articles(articles, tmp_path)

    assert paths == [tmp_path / '001.txt']
    assert paths[0].read_text(encoding='utf-8') == (
        '제목: 수집된 뉴스 제목\n'
        '날짜: 2026-04-28\n'
        '기자: 홍길동\n'
        'URL: https://news.example.com/1\n'
        '---\n'
        '수집된 뉴스 본문입니다. 충분한 본문을 그대로 전달합니다.'
    )
