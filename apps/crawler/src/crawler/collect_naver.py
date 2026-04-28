from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

import httpx

from crawler.schemas import CrawledArticle

NAVER_SEARCH_URL = 'https://openapi.naver.com/v1/search/news.json'
DEFAULT_SEEDED_ARTICLES = (
    {'topic': '방시혁, 2000억 부당이득 혐의 구속영장 신청', 'url': 'https://www.newsis.com/view/NISX20260421_0003600696'},
    {'topic': '뉴진스, 코펜하겐 포착…민지 합류 미정 컴백 임박', 'url': 'https://www.mt.co.kr/entertainment/2026/04/27/2026042714067299138'},
    {'topic': '위너 송민호, 병역법 위반 징역 1년 6개월 구형', 'url': 'https://www.news1.kr/society/court-prosecution/6143557'},
    {'topic': '어도어, 다니엘·민희진에 431억 손해배상 청구 소송', 'url': 'https://www.newsis.com/view/NISX20260325_0003563829'},
    {'topic': '위너 송민호, 부실 복무 이유 묻자 즉답 회피', 'url': 'https://imnews.imbc.com/news/2026/society/article/6816838_36918.html'},
)
TARGET_BODY_MARKERS = ('dic_area', 'articleBodyContents', 'go_trans', '_article_content')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

SearchItems = Callable[[str, int], list[dict[str, Any]]]
FetchHtml = Callable[[str], str]


class _TextExtractor(HTMLParser):
    def __init__(self, *, target_only: bool = False):
        super().__init__()
        self.target_only = target_only
        self._capture_depth = 0 if target_only else 1
        self._skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {'script', 'style'}:
            self._skip_depth += 1
            return
        attr_text = ' '.join(value or '' for _, value in attrs)
        if self.target_only and self._capture_depth == 0 and any(marker in attr_text for marker in TARGET_BODY_MARKERS):
            self._capture_depth = 1
            return
        if self._capture_depth > 0:
            self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth > 0:
            self._skip_depth -= 1
            return
        if self._capture_depth > 0:
            self._capture_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and self._capture_depth > 0:
            self.parts.append(data)

    @property
    def text(self) -> str:
        return re.sub(r'\s+', ' ', unescape(' '.join(self.parts))).strip()


def _strip_html(value: str | None) -> str:
    if not value:
        return ''
    parser = _TextExtractor()
    parser.feed(value)
    return parser.text


def _format_pub_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, '%a, %d %b %Y %H:%M:%S %z').strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return value


def _extract_body(html: str) -> str:
    if not html:
        return ''
    parser = _TextExtractor(target_only=True)
    parser.feed(html)
    if parser.text:
        return parser.text
    article_match = re.search(r'<article\b[^>]*>(.*?)</article>', html, flags=re.IGNORECASE | re.DOTALL)
    if article_match:
        return _strip_html(article_match.group(1))
    return _strip_html(html)


def _extract_meta_content(html: str, *names: str) -> str:
    for name in names:
        pattern = rf'<meta\b(?=[^>]*(?:property|name)=["\']{re.escape(name)}["\'])(?=[^>]*content=["\']([^"\']+)["\'])[^>]*>'
        match = re.search(pattern, html, flags=re.IGNORECASE)
        if match:
            return _strip_html(match.group(1))
    return ''


def _hostname(url: str) -> str:
    match = re.match(r'https?://([^/]+)', url)
    return match.group(1).removeprefix('www.') if match else ''


def search_naver_items(query: str, count: int) -> list[dict[str, Any]]:
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise EnvironmentError('NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경 변수가 필요합니다.')

    with httpx.Client(timeout=10, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(
            NAVER_SEARCH_URL,
            headers={
                'X-Naver-Client-Id': client_id,
                'X-Naver-Client-Secret': client_secret,
            },
            params={'query': query, 'display': count, 'sort': 'date'},
        )
        response.raise_for_status()
        return [item for item in response.json().get('items', []) if isinstance(item, dict)]


def fetch_article_html(url: str) -> str:
    with httpx.Client(timeout=10, headers=HEADERS, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def collect_naver_articles(
    query: str,
    count: int,
    *,
    search_items: SearchItems = search_naver_items,
    fetch_html: FetchHtml = fetch_article_html,
) -> list[CrawledArticle]:
    articles: list[CrawledArticle] = []
    for item in search_items(query, count):
        title = _strip_html(str(item.get('title', '')))
        description = _strip_html(str(item.get('description', '')))
        naver_link = str(item.get('link') or '')
        original_link = str(item.get('originallink') or naver_link)
        if not title or not original_link:
            continue

        body = ''
        if 'news.naver.com' in naver_link:
            try:
                body = _extract_body(fetch_html(naver_link))
            except Exception:
                body = ''
        content = body or description
        if not content:
            continue

        articles.append(
            CrawledArticle(
                title=title,
                content=content,
                url=original_link,
                date=_format_pub_date(str(item.get('pubDate') or '')),
                media='naver-news',
                scraped_at=datetime.now(),
            )
        )
    return articles


def collect_seeded_articles(
    seeds: list[dict[str, str]] | tuple[dict[str, str], ...] = DEFAULT_SEEDED_ARTICLES,
    *,
    fetch_html: FetchHtml = fetch_article_html,
) -> list[CrawledArticle]:
    articles: list[CrawledArticle] = []
    for seed in seeds:
        url = seed.get('url', '')
        if not url:
            continue
        try:
            html = fetch_html(url)
        except Exception:
            continue
        title = _extract_meta_content(html, 'og:title', 'twitter:title') or seed.get('topic', '')
        content = _extract_body(html)
        if not title or not content:
            continue
        articles.append(
            CrawledArticle(
                title=title,
                content=content,
                url=url,
                date=datetime.now().strftime('%Y-%m-%d %H:%M'),
                media=_extract_meta_content(html, 'og:site_name', 'twitter:site') or _hostname(url),
                scraped_at=datetime.now(),
            )
        )
    return articles


def _json_ready(article: CrawledArticle) -> dict[str, Any]:
    payload = article.model_dump(mode='json')
    payload['url'] = str(article.url)
    return payload


def save_latest_articles(articles: list[CrawledArticle], output_dir: Path, *, query: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = [_json_ready(article) for article in articles]
    latest_path = output_dir / 'latest.json'
    snapshot_path = output_dir / f'{query}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    latest_path.write_text(text, encoding='utf-8')
    snapshot_path.write_text(text, encoding='utf-8')
    return latest_path, snapshot_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Collect real Naver news into apps/crawler/output/latest.json')
    parser.add_argument('--query', default='사회', help='Naver news search query')
    parser.add_argument('--count', default=20, type=int, help='Number of articles to request')
    parser.add_argument('--source', choices=('naver-search', 'seeded'), default='naver-search')
    parser.add_argument('--output-dir', default=Path('output'), type=Path, help='Crawler output directory')
    args = parser.parse_args()

    if args.source == 'seeded':
        articles = collect_seeded_articles()
    else:
        articles = collect_naver_articles(args.query, args.count)
    latest_path, snapshot_path = save_latest_articles(articles, args.output_dir, query=args.query)
    print(f'collected {len(articles)} articles')
    print(f'latest: {latest_path}')
    print(f'snapshot: {snapshot_path}')


if __name__ == '__main__':
    main()
