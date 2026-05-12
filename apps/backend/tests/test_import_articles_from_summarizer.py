from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.infrastructure.database import Base
from app.infrastructure.models import ArticleModel
from app.scripts.import_articles_from_summarizer import import_summarized_articles


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')


def write_dataset(base: Path, title: str, summary: str, article_id: str = '001', url: str = 'https://example.com/news/1') -> None:
    write_json(
        base / 'json' / f'{article_id}.json',
        {
            'title': title,
            'date': '2026-04-28',
            'author': '김기자',
            'url': url,
            'content': '실제 본문입니다. 뉴스 홈 상세 화면에서 보여줄 충분한 기사 본문입니다.',
        },
    )
    write_json(
        base / 'summarized' / f'{article_id}.json',
        {
            'headline_34': title,
            'headline_58': title,
            'headline_89': title,
            'summary': summary,
        },
    )
    write_json(base / 'verified' / f'{article_id}.json', {'verdict': 'clean', '_article_id': article_id, '_title': title})
    write_json(base / 'category_map.json', [{'article_id': article_id, 'primary_category': '경제', 'subcategory': '증권'}])


def write_run_manifest(base: Path, *, article_ids: list[str], complete: bool) -> None:
    write_json(base / 'run_manifest.json', {'article_ids': article_ids, 'complete': complete})


def make_session() -> Session:
    engine = create_engine('sqlite+pysqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def test_import_summarized_articles_inserts_rows_into_existing_database(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약')
    session = make_session()

    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 1
    assert stats.updated == 0
    article = session.get(ArticleModel, 'SUM-001')
    assert article is not None
    assert article.title == '첫 번째 제목'
    assert article.summary == '첫 번째 요약'
    assert article.primary_category == 'stock'
    assert article.subcategory == 'stock-domestic'


def test_import_summarized_articles_skips_non_clean_verifications(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약')
    write_json(tmp_path / 'verified' / '001.json', {'verdict': 'suspicious', '_article_id': '001', '_title': '첫 번째 제목'})
    session = make_session()

    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 0
    assert stats.updated == 0
    assert session.get(ArticleModel, 'SUM-001') is None


def test_import_summarized_articles_updates_existing_rows_without_duplicate_insert(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약')
    session = make_session()
    import_summarized_articles(session, tmp_path)

    write_dataset(tmp_path, '수정된 제목', '수정된 요약')
    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 0
    assert stats.updated == 1
    rows = session.scalars(select(ArticleModel)).all()
    assert len(rows) == 1
    assert rows[0].title == '수정된 제목'
    assert rows[0].summary == '수정된 요약'


def test_import_summarized_articles_removes_stale_summarizer_rows_absent_from_latest_dataset(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약', article_id='001', url='https://example.com/news/1')
    write_run_manifest(tmp_path, article_ids=['001'], complete=True)
    session = make_session()
    import_summarized_articles(session, tmp_path)

    for child in tmp_path.iterdir():
        if child.is_dir():
            for file in child.iterdir():
                file.unlink()
    write_dataset(tmp_path, '두 번째 제목', '두 번째 요약', article_id='002', url='https://example.com/news/2')
    write_run_manifest(tmp_path, article_ids=['002'], complete=True)

    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 1
    assert stats.updated == 0
    assert stats.deleted == 1
    rows = session.scalars(select(ArticleModel).order_by(ArticleModel.id)).all()
    assert [row.id for row in rows] == ['SUM-002']


def test_import_summarized_articles_does_not_remove_stale_rows_without_complete_run_manifest(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약', article_id='001', url='https://example.com/news/1')
    write_run_manifest(tmp_path, article_ids=['001'], complete=True)
    session = make_session()
    import_summarized_articles(session, tmp_path)

    for child in tmp_path.iterdir():
        if child.is_dir():
            for file in child.iterdir():
                file.unlink()
        elif child.is_file():
            child.unlink()
    write_dataset(tmp_path, '두 번째 제목', '두 번째 요약', article_id='002', url='https://example.com/news/2')

    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 1
    assert stats.updated == 0
    assert stats.deleted == 0
    rows = session.scalars(select(ArticleModel).order_by(ArticleModel.id)).all()
    assert [row.id for row in rows] == ['SUM-001', 'SUM-002']


def test_import_summarized_articles_matches_existing_rows_by_original_url_when_id_changes(tmp_path: Path):
    write_dataset(tmp_path, '첫 번째 제목', '첫 번째 요약', article_id='001', url='https://example.com/news/same')
    session = make_session()
    import_summarized_articles(session, tmp_path)

    for child in tmp_path.iterdir():
        if child.is_dir():
            for file in child.iterdir():
                file.unlink()
    write_dataset(tmp_path, 'URL 기준 수정 제목', 'URL 기준 수정 요약', article_id='002', url='https://example.com/news/same')

    stats = import_summarized_articles(session, tmp_path)

    assert stats.inserted == 0
    assert stats.updated == 1
    assert stats.deleted == 0
    rows = session.scalars(select(ArticleModel)).all()
    assert len(rows) == 1
    assert rows[0].id == 'SUM-001'
    assert rows[0].title == 'URL 기준 수정 제목'
