from __future__ import annotations

from pathlib import Path

from crawler.schemas import CrawledArticle


def render_summarizer_raw(article: CrawledArticle) -> str:
    return (
        f"제목: {article.title}\n"
        f"날짜: {article.date or ''}\n"
        f"기자: {article.author or ''}\n"
        f"URL: {article.url}\n"
        f"---\n"
        f"{article.content}"
    )


def save_raw_articles(articles: list[CrawledArticle], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, article in enumerate(articles, start=1):
        path = output_dir / f"{index:03d}.txt"
        path.write_text(render_summarizer_raw(article), encoding='utf-8')
        paths.append(path)
    return paths
