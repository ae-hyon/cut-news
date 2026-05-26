from __future__ import annotations

import argparse
import json
import shutil
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
    article_id = _pick(payload, 'article_id')
    content_source = _pick(payload, 'content_source')
    if not (title and content and url):
        return None
    try:
        return CrawledArticle(
            article_id=str(article_id) if article_id else None,
            title=str(title),
            content=str(content),
            url=str(url),
            date=str(date) if date else None,
            author=str(author) if author else None,
            media=str(media) if media else None,
            content_source=str(content_source) if content_source else None,
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
    for index, item in enumerate(_extract_items(payload), start=1):
        article = _normalise_article(item)
        if article is not None:
            if article.article_id is None:
                article.article_id = f'raw-{index:03d}'
            articles.append(article)
    return articles


def _clear_directory(path: Path, *, suffixes: tuple[str, ...] | None = None) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file():
            if suffixes is None or child.suffix in suffixes:
                child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)


def export_articles_to_raw(
    input_path: Path,
    output_dir: Path,
    *,
    clear: bool = False,
    clear_derived_dirs: list[Path] | None = None,
    max_articles: int | None = None,
) -> list[Path]:
    if clear:
        _clear_directory(output_dir, suffixes=('.txt',))
        for derived_dir in clear_derived_dirs or []:
            _clear_directory(derived_dir)
    articles = load_articles_from_json(input_path)
    if max_articles is not None and max_articles > 0:
        articles = articles[:max_articles]
    return save_raw_articles(articles, output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description='Export crawler JSON output to summarizer data/raw/*.txt')
    parser.add_argument('--input', required=True, type=Path, help='crawler output JSON file')
    parser.add_argument('--output-dir', required=True, type=Path, help='summarizer raw output directory')
    parser.add_argument('--clear', action='store_true', help='remove stale raw files before writing new ones')
    parser.add_argument(
        '--clear-derived-dir',
        action='append',
        default=[],
        type=Path,
        help='also clear downstream summarizer output directories so the next pipeline run only uses the latest raw dataset',
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=None,
        help='optional cap on exported raw articles for bounded smoke runs; values <= 0 mean no cap',
    )
    args = parser.parse_args()

    paths = export_articles_to_raw(
        args.input,
        args.output_dir,
        clear=args.clear,
        clear_derived_dirs=args.clear_derived_dir,
        max_articles=args.max_articles,
    )
    print(f'exported {len(paths)} articles to {args.output_dir}')


if __name__ == '__main__':
    main()
