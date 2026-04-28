from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from crawler.pipeline import save_raw_articles
from crawler.schemas import CrawledArticle


def _pick(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value not in (None, ''):
            return value
    return None


def _normalise_article(payload: dict[str, Any]) -> CrawledArticle | None:
    title = _pick(payload, 'title', '제목')
    content = _pick(payload, 'content', '본문', 'body', 'description')
    url = _pick(payload, 'url', '링크', 'link', 'original_url', 'originallink')
    date = _pick(payload, 'date', '날짜', 'published_at', 'pubDate')
    author = _pick(payload, 'author', '기자')
    media = _pick(payload, 'media', '언론사', 'source')
    if not (title and content and url):
        return None
    try:
        return CrawledArticle(
            title=str(title),
            content=str(content),
            url=str(url),
            date=str(date) if date else None,
            author=str(author) if author else None,
            media=str(media) if media else None,
        )
    except ValidationError:
        return None


def _extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ('articles', 'items', 'results', 'data'):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]
    return []


def load_articles_from_json(path: Path) -> list[CrawledArticle]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    articles: list[CrawledArticle] = []
    for item in _extract_items(payload):
        article = _normalise_article(item)
        if article is not None:
            articles.append(article)
    return articles


def main() -> None:
    parser = argparse.ArgumentParser(description='Export crawler JSON output to summarizer data/raw/*.txt')
    parser.add_argument('--input', required=True, type=Path, help='crawler output JSON file')
    parser.add_argument('--output-dir', required=True, type=Path, help='summarizer raw output directory')
    args = parser.parse_args()

    articles = load_articles_from_json(args.input)
    paths = save_raw_articles(articles, args.output_dir)
    print(f'exported {len(paths)} articles to {args.output_dir}')


if __name__ == '__main__':
    main()
