from __future__ import annotations

import json
from pathlib import Path

from crawler.collect_naver import (
    CRAWL_CATEGORIES,
    build_category_queries,
    collect_all_category_articles,
    collect_seeded_articles,
    collect_naver_articles,
    save_latest_articles,
)


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


def test_save_latest_articles_writes_stable_pipeline_input(tmp_path: Path):
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

    latest_path = save_latest_articles(articles, tmp_path, query='사회')

    assert latest_path == tmp_path / 'latest.json'
    latest_payload = json.loads(latest_path.read_text(encoding='utf-8'))
    assert latest_payload[0]['title'] == '저장 테스트 기사'
    assert latest_payload[0]['url'] == 'https://example.com/original/1'


def test_category_crawl_plan_matches_service_taxonomy():
    assert [category['id'] for category in CRAWL_CATEGORIES] == [
        'stock',
        'crypto',
        'realestate',
        'politics',
        'economy',
        'tech',
        'entertainment',
        'sports',
        'global',
        'lifestyle',
    ]
    assert {subcategory['id'] for category in CRAWL_CATEGORIES for subcategory in category['subcategories']} >= {
        'stock-domestic',
        'crypto-bitcoin',
        'realestate-lease',
        'politics-policy',
        'economy-finance',
        'tech-ai',
        'entertainment-kpop',
        'sports-esports',
        'global-us',
        'lifestyle-health',
    }


def test_build_category_queries_covers_every_category_with_keywords_and_subcategories():
    queries = build_category_queries()

    categories = {query.category_id for query in queries}
    assert categories == {category['id'] for category in CRAWL_CATEGORIES}
    assert ('stock', '코스피') in {(query.category_id, query.query) for query in queries}
    assert ('stock', '국내주식') in {(query.category_id, query.query) for query in queries}
    assert ('global', '미국') in {(query.category_id, query.query) for query in queries}
    assert ('lifestyle', '맛집') in {(query.category_id, query.query) for query in queries}


def test_collect_all_category_articles_dedupes_across_category_queries_and_keeps_source_metadata():
    requested_queries: list[tuple[str, int]] = []

    def fake_search(query: str, count: int):
        requested_queries.append((query, count))
        if query == '코스피':
            return [
                {
                    'title': '코스피 기사',
                    'description': '코스피 기사 본문입니다.',
                    'link': 'https://example.com/list/stock-1',
                    'originallink': 'https://example.com/original/shared',
                }
            ]
        if query == '국내주식':
            return [
                {
                    'title': '코스피 기사 중복',
                    'description': '중복 본문입니다.',
                    'link': 'https://example.com/list/stock-duplicate',
                    'originallink': 'https://example.com/original/shared',
                }
            ]
        return []

    articles, stats = collect_all_category_articles(
        [
            {'category_id': 'stock', 'query': '코스피'},
            {'category_id': 'stock', 'query': '국내주식'},
        ],
        count_per_query=3,
        search_items=fake_search,
        fetch_html=lambda url: '',
    )

    assert requested_queries == [('코스피', 3), ('국내주식', 3)]
    assert len(articles) == 1
    assert articles[0].source_category == 'stock'
    assert articles[0].source_query == '코스피'
    assert stats['by_category']['stock']['requested_count'] == 6
    assert stats['by_category']['stock']['collected_count'] == 1
    assert stats['deduped_count'] == 1
