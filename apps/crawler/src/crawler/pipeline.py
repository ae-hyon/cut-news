from __future__ import annotations

from pathlib import Path

from crawler.schemas import CrawledArticle


def render_summarizer_raw(article: CrawledArticle) -> str:
    metadata_lines = [
        f"제목: {article.title}",
        f"날짜: {article.date or ''}",
        f"기자: {article.author or ''}",
        f"URL: {article.url}",
    ]
    if article.content_source:
        metadata_lines.append(f"콘텐츠소스: {article.content_source}")
    if article.source_category:
        metadata_lines.append(f"소스카테고리: {article.source_category}")
    if article.source_query:
        metadata_lines.append(f"소스쿼리: {article.source_query}")
    return "\n".join([*metadata_lines, "---", article.content])


def save_raw_articles(articles: list[CrawledArticle], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, article in enumerate(articles, start=1):
        article_id = article.article_id or f'raw-{index:03d}'
        path = output_dir / f"{article_id}.txt"
        path.write_text(render_summarizer_raw(article), encoding='utf-8')
        paths.append(path)
    return paths
