from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.entities import DailyFeedSnapshot, DailyFeedSnapshotItem, UserPreference
from app.domain.enums import PreferenceMode
from app.infrastructure.database import Base
from app.infrastructure.models import ArticleModel, UserPreferenceModel
from app.infrastructure.repositories import SqlAlchemyDailyFeedSnapshotRepository, SqlAlchemyUserPreferenceRepository
from app.scripts import run_news_pipeline_job


def test_parse_import_stats_extracts_counters_from_stdout():
    output = (
        'noise\n'
        'summarizer article import complete: inserted=3 updated=4 deleted=1 skipped=2\n'
    )

    assert run_news_pipeline_job.parse_import_stats(output) == {
        'inserted': 3,
        'updated': 4,
        'deleted': 1,
        'skipped': 2,
    }


def test_parse_import_observability_extracts_json_payload_from_stdout():
    output = (
        'noise\n'
        'summarizer article import observability: '
        '{"quality_gate_skip_counts":{"low_confidence":2},'
        '"drop_reason_counts":{"category_unmapped":1},'
        '"classification_source_counts":{"keyword_rule":3}}\n'
    )

    assert run_news_pipeline_job.parse_import_observability(output) == {
        'quality_gate_skip_counts': {'low_confidence': 2},
        'drop_reason_counts': {'category_unmapped': 1},
        'classification_source_counts': {'keyword_rule': 3},
    }


def test_parse_crawler_category_stats_extracts_json_payload_from_stdout():
    output = (
        'collected 7 articles\n'
        'crawler category stats: '
        '{"query_count":40,"count_per_query":2,"collected_count":7,"deduped_count":1,'
        '"by_category":{"stock":{"requested_count":14,"collected_count":2}}}\n'
    )

    assert run_news_pipeline_job.parse_crawler_category_stats(output) == {
        'query_count': 40,
        'count_per_query': 2,
        'collected_count': 7,
        'deduped_count': 1,
        'by_category': {'stock': {'requested_count': 14, 'collected_count': 2}},
    }


def test_run_pipeline_job_can_start_from_downloaded_crawl_artifact(tmp_path: Path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / 'run_report.json'
    crawl_input_path = tmp_path / 'artifact' / 'latest.json'
    crawl_report_path = tmp_path / 'artifact' / 'crawl_report.json'
    crawl_input_path.parent.mkdir(parents=True)
    crawl_input_path.write_text('[]', encoding='utf-8')
    crawl_report_path.write_text(
        json.dumps({'query_count': 49, 'count_per_query': 1, 'collected_count': 37, 'deduped_count': 12}),
        encoding='utf-8',
    )
    calls: list[str] = []

    def fake_runner(step_name: str, command: list[str], cwd: Path, env: dict[str, str]):
        calls.append(step_name)
        stdout = ''
        if step_name == 'import':
            stdout = 'summarizer article import complete: inserted=1 updated=0 deleted=0 skipped=0\n'
        return run_news_pipeline_job.StepExecutionResult(
            name=step_name,
            status='success',
            command=command,
            cwd=str(cwd),
            duration_seconds=0.1,
            stdout=stdout,
            stderr='',
            returncode=0,
        )

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='naver-all-categories',
        query='경제',
        count=1,
        runner=fake_runner,
        snapshot_generator=lambda feed_date, generation_source: run_news_pipeline_job.SnapshotGenerationResult(),
        crawl_input_path=crawl_input_path,
        crawl_report_path=crawl_report_path,
    )

    assert calls == ['export_raw', 'summarize', 'import']
    assert report['crawl_input_path'] == str(crawl_input_path)
    assert report['crawl_report_path'] == str(crawl_report_path)
    assert report['crawler_category_stats'] == {
        'query_count': 49,
        'count_per_query': 1,
        'collected_count': 37,
        'deduped_count': 12,
    }
    steps = report['steps']
    assert isinstance(steps, list)
    export_step = next(step for step in steps if step['name'] == 'export_raw')
    assert str(crawl_input_path) in export_step['command']


def test_run_pipeline_job_writes_success_report_with_step_results_and_snapshot_generation(tmp_path: Path):
    data_dir = tmp_path / 'data'
    for directory in ['raw', 'json', 'scored', 'summarized', 'verified']:
        (data_dir / directory).mkdir(parents=True, exist_ok=True)
    (data_dir / 'raw' / 'a1.txt').write_text('raw', encoding='utf-8')
    (data_dir / 'json' / 'a1.json').write_text('{}', encoding='utf-8')
    (data_dir / 'scored' / 'a1.json').write_text('{}', encoding='utf-8')
    (data_dir / 'summarized' / 'a1.json').write_text('{}', encoding='utf-8')
    (data_dir / 'summarized' / 'a2_error.json').write_text('{}', encoding='utf-8')
    (data_dir / 'verified' / 'a1.json').write_text('{}', encoding='utf-8')
    report_path = data_dir / 'run_report.json'

    calls: list[str] = []

    def fake_runner(step_name: str, command: list[str], cwd: Path, env: dict[str, str]):
        calls.append(step_name)
        stdout = ''
        if step_name == 'collect':
            stdout = (
                'collected 7 articles\n'
                'crawler category stats: '
                '{"query_count":40,"count_per_query":2,"collected_count":7,"deduped_count":1,'
                '"by_category":{"stock":{"requested_count":14,"collected_count":2}}}\n'
            )
        if step_name == 'import':
            stdout = (
                'summarizer article import complete: inserted=1 updated=2 deleted=0 skipped=3\n'
                'summarizer article import observability: '
                '{"quality_gate_skip_counts":{"violations":1},'
                '"drop_reason_counts":{"category_unmapped":2},'
                '"classification_source_counts":{"source_subcategory":1}}\n'
            )
        return run_news_pipeline_job.StepExecutionResult(
            name=step_name,
            status='success',
            command=command,
            cwd=str(cwd),
            duration_seconds=0.25,
            stdout=stdout,
            stderr='',
            returncode=0,
        )

    snapshot_calls: list[tuple[str, str]] = []

    def fake_snapshot_generator(feed_date: str, generation_source: str):
        snapshot_calls.append((feed_date, generation_source))
        return run_news_pipeline_job.SnapshotGenerationResult(
            attempted_user_count=3,
            generated_count=2,
            skipped_viewed_count=1,
            failed_count=0,
        )

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='seeded',
        query='경제',
        count=6,
        max_articles=5,
        runner=fake_runner,
        snapshot_generator=fake_snapshot_generator,
    )

    assert calls == ['collect', 'export_raw', 'summarize', 'import']
    assert snapshot_calls == [(report['feed_date'], 'news-pipeline')]
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    export_step = next(step for step in persisted['steps'] if step['name'] == 'export_raw')
    assert '--max-articles 5' in export_step['command']
    assert report['status'] == 'success'
    assert report['failed_step'] is None
    assert report['max_articles'] == 5
    assert report['import_stats'] == {'inserted': 1, 'updated': 2, 'deleted': 0, 'skipped': 3}
    assert report['crawler_category_stats'] == {
        'query_count': 40,
        'count_per_query': 2,
        'collected_count': 7,
        'deduped_count': 1,
        'by_category': {'stock': {'requested_count': 14, 'collected_count': 2}},
    }
    assert report['quality_gate_skip_counts'] == {'violations': 1}
    assert report['drop_reason_counts'] == {'category_unmapped': 2}
    assert report['classification_source_counts'] == {'source_subcategory': 1}
    assert report['snapshot_generation'] == {
        'attempted_user_count': 3,
        'generated_count': 2,
        'skipped_viewed_count': 1,
        'failed_count': 0,
    }
    assert report['schedule'] == {
        'timezone': 'Asia/Seoul',
        'ai_news_generation_time': '08:30:00',
    }
    assert report_path.exists()
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    assert persisted['status'] == 'success'
    assert persisted['steps'][-1]['name'] == 'import'
    assert persisted['schedule']['ai_news_generation_time'] == '08:30:00'
    assert 'stdout' not in persisted['steps'][-1]

    archived_reports = list((data_dir / 'run_reports').glob('run_*.json'))
    assert len(archived_reports) == 1
    archived = json.loads(archived_reports[0].read_text(encoding='utf-8'))
    assert archived == persisted
    assert persisted['archive_report_path'] == str(archived_reports[0])


def test_run_pipeline_job_does_not_generate_snapshots_when_import_fails(tmp_path: Path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / 'run_report.json'

    def fake_runner(step_name: str, command: list[str], cwd: Path, env: dict[str, str]):
        status = 'failed' if step_name == 'import' else 'success'
        return run_news_pipeline_job.StepExecutionResult(
            name=step_name,
            status=status,
            command=command,
            cwd=str(cwd),
            duration_seconds=0.1,
            stdout='',
            stderr='import boom' if step_name == 'import' else '',
            returncode=1 if step_name == 'import' else 0,
        )

    snapshot_calls: list[tuple[str, str]] = []

    def fake_snapshot_generator(feed_date: str, generation_source: str):
        snapshot_calls.append((feed_date, generation_source))
        return run_news_pipeline_job.SnapshotGenerationResult()

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='seeded',
        query='경제',
        count=4,
        runner=fake_runner,
        snapshot_generator=fake_snapshot_generator,
    )

    assert report['status'] == 'failed'
    assert report['failed_step'] == 'import'
    assert [step['name'] for step in report['steps']] == ['collect', 'export_raw', 'summarize', 'import']
    assert snapshot_calls == []
    assert report['snapshot_generation'] == {
        'attempted_user_count': 0,
        'generated_count': 0,
        'skipped_viewed_count': 0,
        'failed_count': 0,
    }


def test_run_pipeline_job_marks_zero_import_with_drop_reasons_as_failed_and_skips_snapshots(tmp_path: Path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / 'run_report.json'

    def fake_runner(step_name: str, command: list[str], cwd: Path, env: dict[str, str]):
        stdout = ''
        if step_name == 'import':
            stdout = (
                'summarizer article import complete: inserted=0 updated=0 deleted=0 skipped=0\n'
                'summarizer article import observability: '
                '{"quality_gate_skip_counts":{},'
                '"drop_reason_counts":{"summary_error":4,"missing_summary":3},'
                '"classification_source_counts":{}}\n'
            )
        return run_news_pipeline_job.StepExecutionResult(
            name=step_name,
            status='success',
            command=command,
            cwd=str(cwd),
            duration_seconds=0.1,
            stdout=stdout,
            stderr='',
            returncode=0,
        )

    snapshot_calls: list[tuple[str, str]] = []

    def fake_snapshot_generator(feed_date: str, generation_source: str):
        snapshot_calls.append((feed_date, generation_source))
        return run_news_pipeline_job.SnapshotGenerationResult(generated_count=1)

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='naver-all-categories',
        query='경제',
        count=1,
        runner=fake_runner,
        snapshot_generator=fake_snapshot_generator,
    )

    assert report['status'] == 'failed'
    assert report['failed_step'] == 'import'
    assert report['drop_reason_counts'] == {'summary_error': 4, 'missing_summary': 3}
    assert snapshot_calls == []
    assert report['snapshot_generation'] == {
        'attempted_user_count': 0,
        'generated_count': 0,
        'skipped_viewed_count': 0,
        'failed_count': 0,
    }


def test_generate_daily_snapshots_counts_generated_skipped_viewed_and_failed_users(monkeypatch):
    engine = create_engine('sqlite+pysqlite:///:memory:', future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with session_local() as db:
        preference_repository = SqlAlchemyUserPreferenceRepository(db)
        for user_id, completed in [('fresh-user', True), ('viewed-user', True), ('pending-user', False)]:
            preference_repository.save(
                UserPreference(
                    user_id=user_id,
                    mode=PreferenceMode.WIDE,
                    primary_categories=['economy'],
                    subcategories=[],
                    onboarding_completed=completed,
                )
            )
        db.add(
            ArticleModel(
                id='A1',
                title='경제 뉴스',
                summary='s',
                content='c',
                primary_category='economy',
                subcategory='macro',
                published_at='2026-05-19',
                original_url='https://news.example/a1',
                score_weight=0.95,
            )
        )
        db.add(UserPreferenceModel(user_id='broken-user', mode='broken-mode', onboarding_completed=True))
        db.commit()

        snapshot_repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        viewed_snapshot = snapshot_repository.save(
            DailyFeedSnapshot(
                user_id='viewed-user',
                feed_date='2026-05-20',
                status='viewed',
                generated_at=datetime(2026, 5, 20, 0, 30, tzinfo=UTC),
                first_viewed_at=datetime(2026, 5, 20, 8, 0, tzinfo=UTC),
                preference_mode=PreferenceMode.WIDE,
                primary_categories=['economy'],
                subcategories=[],
                generation_source='previous-run',
                items=[DailyFeedSnapshotItem(article_id='A1', block_key='economy-block', block_title='economy block', sort_order=1, score_weight=0.95)],
            )
        )

    monkeypatch.setattr('app.infrastructure.database.SessionLocal', session_local)

    result = run_news_pipeline_job.generate_daily_snapshots('2026-05-20', 'news-pipeline')

    assert result == run_news_pipeline_job.SnapshotGenerationResult(
        attempted_user_count=3,
        generated_count=1,
        skipped_viewed_count=1,
        failed_count=1,
    )
    with session_local() as db:
        snapshot_repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        fresh_snapshot = snapshot_repository.get_by_user_date('fresh-user', '2026-05-20')
        preserved_snapshot = snapshot_repository.get_by_user_date('viewed-user', '2026-05-20')
        pending_snapshot = snapshot_repository.get_by_user_date('pending-user', '2026-05-20')

    assert fresh_snapshot is not None
    assert fresh_snapshot.generation_source == 'news-pipeline'
    assert preserved_snapshot is not None
    assert preserved_snapshot.id == viewed_snapshot.id
    assert preserved_snapshot.generation_source == 'previous-run'
    assert pending_snapshot is None


def test_run_pipeline_job_stops_on_failed_step_and_records_failure(tmp_path: Path):
    data_dir = tmp_path / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    report_path = data_dir / 'run_report.json'

    def fake_runner(step_name: str, command: list[str], cwd: Path, env: dict[str, str]):
        if step_name == 'summarize':
            return run_news_pipeline_job.StepExecutionResult(
                name=step_name,
                status='failed',
                command=command,
                cwd=str(cwd),
                duration_seconds=0.4,
                stdout='',
                stderr='boom',
                returncode=1,
            )
        return run_news_pipeline_job.StepExecutionResult(
            name=step_name,
            status='success',
            command=command,
            cwd=str(cwd),
            duration_seconds=0.1,
            stdout='',
            stderr='',
            returncode=0,
        )

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='seeded',
        query='경제',
        count=4,
        runner=fake_runner,
    )

    assert report['status'] == 'failed'
    assert report['failed_step'] == 'summarize'
    assert [step['name'] for step in report['steps']] == ['collect', 'export_raw', 'summarize']
    assert report['steps'][-1]['error_tail'] == 'boom'
    assert report['import_stats'] == {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    assert report['quality_gate_skip_counts'] == {}
    assert report['drop_reason_counts'] == {}
    assert report['classification_source_counts'] == {}
    assert report['snapshot_generation'] == {
        'attempted_user_count': 0,
        'generated_count': 0,
        'skipped_viewed_count': 0,
        'failed_count': 0,
    }
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    assert persisted['failed_step'] == 'summarize'
    archived_reports = list((data_dir / 'run_reports').glob('run_*.json'))
    assert len(archived_reports) == 1
    assert json.loads(archived_reports[0].read_text(encoding='utf-8'))['failed_step'] == 'summarize'
