from __future__ import annotations

import json
from pathlib import Path

from crawler.collect_naver import collect_seeded_articles, collect_naver_articles, save_latest_articles


def test_collect_naver_articles_turns_search_items_and_scraped_body_into_crawled_articles():
    def fake_search(query: str, count: int):
        assert query == '사회'
        assert count == 1
        return [
            {
                'title': '<b>사회</b> 테스트 기사',
                'description': '<b>요약</b> 설명입니다.',
                'link': 'https://news.naver.com/article/001/0000000001',
                'originallink': 'https://example.com/original/1',
                'pubDate': 'Tue, 28 Apr 2026 10:00:00 +0900',
            }
        ]

    def fake_fetch_html(url: str) -> str:
        assert url == 'https://news.naver.com/article/001/0000000001'
        return '<html><body><article id="dic_area">실제 기사 본문입니다. 충분한 길이의 본문입니다.</article></body></html>'

    articles = collect_naver_articles('사회', 1, search_items=fake_search, fetch_html=fake_fetch_html)

    assert len(articles) == 1
    assert articles[0].title == '사회 테스트 기사'
    assert articles[0].content == '실제 기사 본문입니다. 충분한 길이의 본문입니다.'
    assert str(articles[0].url) == 'https://example.com/original/1'
    assert articles[0].date == '2026-04-28 10:00'
    assert articles[0].media == 'naver-news'
    assert articles[0].article_id


def test_collect_naver_articles_falls_back_to_description_when_body_scrape_is_empty():
    def fake_search(query: str, count: int):
        return [
            {
                'title': '본문 없는 기사',
                'description': 'API 설명을 fallback 본문으로 씁니다.',
                'link': 'https://example.com/list/1',
                'originallink': 'https://example.com/original/1',
                'pubDate': 'bad-date',
            }
        ]

    articles = collect_naver_articles('사회', 1, search_items=fake_search, fetch_html=lambda url: '')

    assert len(articles) == 1
    assert articles[0].content == 'API 설명을 fallback 본문으로 씁니다.'
    assert articles[0].date == 'bad-date'
    assert articles[0].content_source == 'description'


def test_collect_seeded_articles_scrapes_direct_article_urls_without_naver_credentials():
    def fake_fetch_html(url: str) -> str:
        assert url == 'https://example.com/direct/1'
        return '''
        <html>
          <head><meta property="og:title" content="직접 URL 기사"></head>
          <body><article>직접 URL에서 가져온 기사 본문입니다. 충분한 길이입니다.</article></body>
        </html>
        '''

    articles = collect_seeded_articles(
        [{'topic': '직접 URL', 'url': 'https://example.com/direct/1'}],
        fetch_html=fake_fetch_html,
    )

    assert len(articles) == 1
    assert articles[0].title == '직접 URL 기사'
    assert articles[0].content == '직접 URL에서 가져온 기사 본문입니다. 충분한 길이입니다.'
    assert str(articles[0].url) == 'https://example.com/direct/1'
    assert articles[0].media == 'example.com'


def test_collect_naver_articles_dedupes_same_original_article_and_keeps_stable_article_id():
    def fake_search(query: str, count: int):
        return [
            {
                'title': '중복 기사 A',
                'description': '첫 번째 결과',
                'link': 'https://news.naver.com/article/001/0000000001',
                'originallink': 'https://example.com/original/dupe',
                'pubDate': 'Tue, 28 Apr 2026 10:00:00 +0900',
            },
            {
                'title': '중복 기사 A',
                'description': '두 번째 결과',
                'link': 'https://news.naver.com/article/001/0000000999',
                'originallink': 'https://example.com/original/dupe',
                'pubDate': 'Tue, 28 Apr 2026 10:05:00 +0900',
            },
        ]

    def fake_fetch_html(url: str) -> str:
        return '<html><body><article id="dic_area">실제 기사 본문입니다. 충분한 길이의 본문입니다.</article></body></html>'

    articles = collect_naver_articles('경제', 2, search_items=fake_search, fetch_html=fake_fetch_html)

    assert len(articles) == 1
    assert articles[0].article_id == 'bc5a6db53ff4'


def test_save_latest_articles_writes_stable_pipeline_input_and_timestamped_copy(tmp_path: Path):
    articles = collect_naver_articles(
        '사회',
        1,
        search_items=lambda query, count: [
            {
                'title': '저장 테스트 기사',
                'description': '저장 테스트 본문입니다.',
                'link': 'https://example.com/list/1',
                'originallink': 'https://example.com/original/1',
            }
        ],
        fetch_html=lambda url: '',
    )

    latest_path, snapshot_path = save_latest_articles(articles, tmp_path, query='사회')

    assert latest_path == tmp_path / 'latest.json'
    assert snapshot_path.name.startswith('사회_')
    assert snapshot_path.suffix == '.json'
    latest_payload = json.loads(latest_path.read_text(encoding='utf-8'))
    snapshot_payload = json.loads(snapshot_path.read_text(encoding='utf-8'))
    assert latest_payload == snapshot_payload
    assert latest_payload[0]['title'] == '저장 테스트 기사'
    assert latest_payload[0]['url'] == 'https://example.com/original/1'
