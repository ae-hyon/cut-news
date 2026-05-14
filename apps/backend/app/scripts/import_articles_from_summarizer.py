from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.services.article_ingest_service import ArticleIngestRow, load_summarized_articles_report
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


@dataclass(frozen=True)
class ImportObservability:
    quality_gate_skip_counts: dict[str, int]
    drop_reason_counts: dict[str, int]
    classification_source_counts: dict[str, int]


@dataclass(frozen=True)
class ImportResult:
    stats: ImportStats
    observability: ImportObservability

    @property
    def inserted(self) -> int:
        return self.stats.inserted

    @property
    def updated(self) -> int:
        return self.stats.updated

    @property
    def deleted(self) -> int:
        return self.stats.deleted

    @property
    def skipped(self) -> int:
        return self.stats.skipped

    @property
    def total(self) -> int:
        return self.stats.total


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
) -> ImportResult:
    rows, report = load_summarized_articles_report(data_dir)
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
    stats = ImportStats(inserted=inserted, updated=updated, deleted=deleted, skipped=0)
    observability = ImportObservability(
        quality_gate_skip_counts=dict(report.get('quality_gate_skip_counts', {})),
        drop_reason_counts=dict(report.get('drop_reason_counts', {})),
        classification_source_counts=dict(report.get('classification_source_counts', {})),
    )
    return ImportResult(stats=stats, observability=observability)


def main() -> None:
    data_dir = settings.news_summarizer_dir / 'data'
    if settings.migrate_on_startup:
        run_migrations()
    with SessionLocal() as session:
        result = import_summarized_articles(session, data_dir)
    stats = result.stats
    print(
        'summarizer article import complete: '
        f'inserted={stats.inserted} updated={stats.updated} deleted={stats.deleted} skipped={stats.skipped}'
    )
    print(
        'summarizer article import observability: ' + json.dumps(
            {
                'quality_gate_skip_counts': result.observability.quality_gate_skip_counts,
                'drop_reason_counts': result.observability.drop_reason_counts,
                'classification_source_counts': result.observability.classification_source_counts,
            },
            ensure_ascii=False,
            separators=(',', ':'),
        )
    )


if __name__ == '__main__':
    main()
