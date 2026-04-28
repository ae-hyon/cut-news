from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.article_ingest_service import ArticleIngestRow, load_summarized_articles
from app.common.config import settings
from app.infrastructure.database import SessionLocal, run_migrations
from app.infrastructure.models import ArticleModel


@dataclass(frozen=True)
class ImportStats:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.skipped


def _apply_article_row(model: ArticleModel, row: ArticleIngestRow) -> None:
    model.title = row.title
    model.summary = row.summary
    model.content = row.content
    model.primary_category = row.primary_category
    model.subcategory = row.subcategory
    model.published_at = row.published_at
    model.original_url = row.original_url
    model.score_weight = row.score_weight


def import_summarized_articles(session: Session, data_dir: Path) -> ImportStats:
    rows = load_summarized_articles(data_dir)
    inserted = 0
    updated = 0

    for row in rows:
        existing = session.get(ArticleModel, row.id)
        if existing is None:
            existing = session.scalar(select(ArticleModel).where(ArticleModel.original_url == row.original_url))
        if existing is None:
            session.add(ArticleModel(**row.model_dump()))
            inserted += 1
        else:
            _apply_article_row(existing, row)
            updated += 1

    session.commit()
    return ImportStats(inserted=inserted, updated=updated, skipped=0)


def main() -> None:
    data_dir = settings.news_summarizer_dir / 'data'
    if settings.migrate_on_startup:
        run_migrations()
    with SessionLocal() as session:
        stats = import_summarized_articles(session, data_dir)
    print(
        'summarizer article import complete: '
        f'inserted={stats.inserted} updated={stats.updated} skipped={stats.skipped}'
    )


if __name__ == '__main__':
    main()
