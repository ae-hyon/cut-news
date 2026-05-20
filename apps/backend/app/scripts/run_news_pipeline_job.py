from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / 'apps' / 'summarizer' / 'data'
REPORT_PATH = DATA_DIR / 'run_report.json'
REPORT_ARCHIVE_DIR_NAME = 'run_reports'
IMPORT_STATS_PATTERN = re.compile(
    r'inserted=(?P<inserted>\d+)\s+updated=(?P<updated>\d+)\s+deleted=(?P<deleted>\d+)\s+skipped=(?P<skipped>\d+)'
)
IMPORT_OBSERVABILITY_PATTERN = re.compile(r'summarizer article import observability:\s*(?P<payload>\{.*\})')


@dataclass(frozen=True)
class StepExecutionResult:
    name: str
    status: str
    command: list[str]
    cwd: str
    duration_seconds: float
    stdout: str
    stderr: str
    returncode: int


@dataclass(frozen=True)
class SnapshotGenerationResult:
    attempted_user_count: int = 0
    generated_count: int = 0
    skipped_viewed_count: int = 0
    failed_count: int = 0


Runner = Callable[[str, list[str], Path, dict[str, str]], StepExecutionResult]
SnapshotGenerator = Callable[[str, str], SnapshotGenerationResult]


def parse_import_stats(output: str) -> dict[str, int]:
    match = IMPORT_STATS_PATTERN.search(output)
    if not match:
        return {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    return {key: int(value) for key, value in match.groupdict().items()}


def parse_import_observability(output: str) -> dict[str, dict[str, int]]:
    match = IMPORT_OBSERVABILITY_PATTERN.search(output)
    if not match:
        return {
            'quality_gate_skip_counts': {},
            'drop_reason_counts': {},
            'classification_source_counts': {},
        }
    try:
        payload = json.loads(match.group('payload'))
    except json.JSONDecodeError:
        return {
            'quality_gate_skip_counts': {},
            'drop_reason_counts': {},
            'classification_source_counts': {},
        }
    return {
        'quality_gate_skip_counts': dict(payload.get('quality_gate_skip_counts') or {}),
        'drop_reason_counts': dict(payload.get('drop_reason_counts') or {}),
        'classification_source_counts': dict(payload.get('classification_source_counts') or {}),
    }


def run_command(step_name: str, command: list[str], cwd: Path, env: dict[str, str]) -> StepExecutionResult:
    started_at = time.time()
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    return StepExecutionResult(
        name=step_name,
        status='success' if completed.returncode == 0 else 'failed',
        command=command,
        cwd=str(cwd),
        duration_seconds=round(time.time() - started_at, 3),
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def _pipeline_steps(repo_root: Path, *, source: str, query: str, count: int) -> list[tuple[str, list[str], Path, dict[str, str]]]:
    python = sys.executable
    crawler_cwd = repo_root / 'apps' / 'crawler'
    summarizer_cwd = repo_root / 'apps' / 'summarizer'
    backend_cwd = repo_root / 'apps' / 'backend'

    collect_env = {**os.environ, 'PYTHONPATH': 'src'}
    summarize_env = {
        **os.environ,
        'PYTHONUNBUFFERED': '1',
        'PIPELINE_LLM_BACKEND': os.environ.get('PIPELINE_LLM_BACKEND', 'codex_exec'),
        'PIPELINE_MODEL': os.environ.get('PIPELINE_MODEL', 'gpt-5.4-mini'),
        'PIPELINE_CODEX_REASONING_EFFORT': os.environ.get('PIPELINE_CODEX_REASONING_EFFORT', 'low'),
    }
    import_env = {
        **os.environ,
        'PYTHONPATH': '.',
        'DATABASE_URL': os.environ.get('DATABASE_URL', 'sqlite+pysqlite:///dev-ui-test.db'),
    }

    return [
        (
            'collect',
            [python, '-m', 'crawler.collect_naver', '--source', source, '--query', query, '--count', str(count), '--output-dir', 'output'],
            crawler_cwd,
            collect_env,
        ),
        (
            'export_raw',
            [
                python,
                '-m',
                'crawler.export_raw',
                '--input',
                '../../apps/crawler/output/latest.json',
                '--output-dir',
                '../../apps/summarizer/data/raw',
                '--clear',
                '--clear-derived-dir',
                '../../apps/summarizer/data/json',
                '--clear-derived-dir',
                '../../apps/summarizer/data/scored',
                '--clear-derived-dir',
                '../../apps/summarizer/data/summarized',
                '--clear-derived-dir',
                '../../apps/summarizer/data/verified',
            ],
            crawler_cwd,
            collect_env,
        ),
        (
            'summarize',
            [python, 'run_pipeline.py', '--from', '2'],
            summarizer_cwd,
            summarize_env,
        ),
        (
            'import',
            [python, '-m', 'app.scripts.import_articles_from_summarizer'],
            backend_cwd,
            import_env,
        ),
    ]


def _serialize_step(step: StepExecutionResult) -> dict[str, object]:
    payload = asdict(step)
    payload['command'] = ' '.join(step.command)
    payload.pop('stdout', None)
    payload.pop('stderr', None)
    if step.status != 'success' and step.stderr:
        payload['error_tail'] = step.stderr[-1000:]
    return payload


def _clear_category_map(repo_root: Path) -> None:
    category_map_path = repo_root / 'apps' / 'summarizer' / 'data' / 'category_map.json'
    if category_map_path.exists():
        category_map_path.unlink()


def _schedule_metadata() -> dict[str, str]:
    return {
        'timezone': os.environ.get('NEWS_SCHEDULE_TIMEZONE', 'Asia/Seoul'),
        'ai_news_generation_time': os.environ.get('AI_NEWS_GENERATION_TIME', '08:30:00'),
    }


def _current_feed_date(timezone_name: str) -> str:
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo('UTC')
    return datetime.now(timezone).date().isoformat()


def generate_daily_snapshots(feed_date: str, generation_source: str = 'news-pipeline') -> SnapshotGenerationResult:
    from app.application.services.daily_feed_snapshot_service import DailyFeedSnapshotService
    from app.application.services.feed_service import FeedService
    from app.infrastructure.database import SessionLocal
    from app.infrastructure.repositories import (
        SqlAlchemyArticleRepository,
        SqlAlchemyDailyFeedSnapshotRepository,
        SqlAlchemyScrapRepository,
        SqlAlchemyUserArticleReadRepository,
        SqlAlchemyUserPreferenceRepository,
    )

    attempted_user_count = 0
    generated_count = 0
    skipped_viewed_count = 0
    failed_count = 0

    with SessionLocal() as db:
        article_repository = SqlAlchemyArticleRepository(db)
        preference_repository = SqlAlchemyUserPreferenceRepository(db)
        snapshot_repository = SqlAlchemyDailyFeedSnapshotRepository(db)
        service = DailyFeedSnapshotService(
            feed_service=FeedService(article_repository, preference_repository, SqlAlchemyScrapRepository(db)),
            preference_repository=preference_repository,
            snapshot_repository=snapshot_repository,
            read_repository=SqlAlchemyUserArticleReadRepository(db),
        )
        user_ids = preference_repository.list_onboarded_user_ids()
        for user_id in user_ids:
            attempted_user_count += 1
            try:
                existing = snapshot_repository.get_by_user_date(user_id, feed_date)
                saved = service.generate_for_user_date(user_id, feed_date, generation_source=generation_source)
            except Exception:
                failed_count += 1
                continue
            if existing is not None and existing.first_viewed_at is not None and saved.id == existing.id:
                skipped_viewed_count += 1
            else:
                generated_count += 1

    return SnapshotGenerationResult(
        attempted_user_count=attempted_user_count,
        generated_count=generated_count,
        skipped_viewed_count=skipped_viewed_count,
        failed_count=failed_count,
    )


def _archive_report_path(data_dir: Path, started_at: str) -> Path:
    safe_started_at = re.sub(r'[^0-9A-Za-z+-]+', '', started_at)
    return data_dir / REPORT_ARCHIVE_DIR_NAME / f'run_{safe_started_at}.json'


def write_run_report(path: Path, payload: dict[str, object], *, archive_path: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    if archive_path is not None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def run_pipeline_job(
    *,
    repo_root: Path = REPO_ROOT,
    data_dir: Path = DATA_DIR,
    report_path: Path = REPORT_PATH,
    source: str,
    query: str,
    count: int,
    runner: Runner = run_command,
    snapshot_generator: SnapshotGenerator = generate_daily_snapshots,
) -> dict[str, object]:
    started_at = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    steps_payload: list[dict[str, object]] = []
    import_stats = {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    import_observability = {
        'quality_gate_skip_counts': {},
        'drop_reason_counts': {},
        'classification_source_counts': {},
    }
    status = 'success'
    failed_step: str | None = None
    schedule = _schedule_metadata()
    feed_date = _current_feed_date(schedule['timezone'])
    snapshot_generation = SnapshotGenerationResult()

    for step_name, command, cwd, env in _pipeline_steps(repo_root, source=source, query=query, count=count):
        result = runner(step_name, command, cwd, env)
        steps_payload.append(_serialize_step(result))
        if step_name == 'export_raw' and result.status == 'success':
            _clear_category_map(repo_root)
        if step_name == 'import':
            import_stats = parse_import_stats(result.stdout)
            import_observability = parse_import_observability(result.stdout)
        if result.status != 'success':
            status = 'failed'
            failed_step = step_name
            break

    if status == 'success':
        snapshot_generation = snapshot_generator(feed_date, 'news-pipeline')

    archive_path = _archive_report_path(data_dir, started_at)
    payload: dict[str, object] = {
        'status': status,
        'failed_step': failed_step,
        'started_at': started_at,
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'source': source,
        'query': query,
        'count': count,
        'feed_date': feed_date,
        'schedule': schedule,
        'steps': steps_payload,
        'import_stats': import_stats,
        'quality_gate_skip_counts': import_observability['quality_gate_skip_counts'],
        'drop_reason_counts': import_observability['drop_reason_counts'],
        'classification_source_counts': import_observability['classification_source_counts'],
        'snapshot_generation': asdict(snapshot_generation),
        'report_path': str(report_path),
        'archive_report_path': str(archive_path),
    }
    write_run_report(report_path, payload, archive_path=archive_path)
    return payload


def main() -> None:
    source = os.environ.get('NEWS_SOURCE', 'seeded')
    query = os.environ.get('NEWS_QUERY', '경제')
    count = int(os.environ.get('NEWS_COUNT', '20'))
    report = run_pipeline_job(source=source, query=query, count=count)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['status'] != 'success':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
