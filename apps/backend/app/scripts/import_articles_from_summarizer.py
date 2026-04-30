from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.article_classifier_service import build_article_classifier
from app.application.services.article_ingest_service import ArticleClassifier, ArticleIngestRow, load_summarized_articles
from app.common.config import settings
from app.infrastructure.database import SessionLocal, run_migrations
from app.infrastructure.models import ArticleModel


@dataclass(frozen=True)
class ImportStats:
    inserted: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        return self.inserted + self.updated + self.deleted + self.skipped


def _apply_article_row(model: ArticleModel, row: ArticleIngestRow) -> None:
    model.title = row.title
    model.summary = row.summary
    model.content = row.content
    model.primary_category = row.primary_category
    model.subcategory = row.subcategory
    model.published_at = row.published_at
    model.original_url = row.original_url
    model.score_weight = row.score_weight


def _can_prune_stale(data_dir: Path) -> bool:
    manifest_path = data_dir / 'run_manifest.json'
    if not manifest_path.exists():
        return False
    try:
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(payload.get('complete'))


def import_summarized_articles(
    session: Session,
    data_dir: Path,
    *,
    classifier: ArticleClassifier | None = None,
) -> ImportStats:
    rows = load_summarized_articles(data_dir, classifier=classifier)
    allow_prune_stale = _can_prune_stale(data_dir)
    inserted = 0
    updated = 0
    retained_ids: set[str] = set()

    for row in rows:
        existing = session.get(ArticleModel, row.id)
        if existing is None:
            existing = session.scalar(select(ArticleModel).where(ArticleModel.original_url == row.original_url))
        if existing is None:
            model = ArticleModel(**row.model_dump())
            session.add(model)
            inserted += 1
            retained_ids.add(model.id)
        else:
            _apply_article_row(existing, row)
            updated += 1
            retained_ids.add(existing.id)

    stale_models = session.scalars(select(ArticleModel).where(ArticleModel.id.like('SUM-%'))).all()
    deleted = 0
    for model in stale_models:
        if model.id in retained_ids or not allow_prune_stale:
            continue
        session.delete(model)
        deleted += 1

    session.commit()
    return ImportStats(inserted=inserted, updated=updated, deleted=deleted, skipped=0)


def main() -> None:
    data_dir = settings.news_summarizer_dir / 'data'
    classifier = build_article_classifier(settings)
    if settings.migrate_on_startup:
        run_migrations()
    with SessionLocal() as session:
        stats = import_summarized_articles(session, data_dir, classifier=classifier)
    print(
        'summarizer article import complete: '
        f'inserted={stats.inserted} updated={stats.updated} deleted={stats.deleted} skipped={stats.skipped}'
    )


if __name__ == '__main__':
    main()
