from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = REPO_ROOT / 'apps' / 'summarizer' / 'data'
REPORT_PATH = DATA_DIR / 'run_report.json'
IMPORT_STATS_PATTERN = re.compile(
    r'inserted=(?P<inserted>\d+)\s+updated=(?P<updated>\d+)\s+deleted=(?P<deleted>\d+)\s+skipped=(?P<skipped>\d+)'
)


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


Runner = Callable[[str, list[str], Path, dict[str, str]], StepExecutionResult]


def parse_import_stats(output: str) -> dict[str, int]:
    match = IMPORT_STATS_PATTERN.search(output)
    if not match:
        return {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    return {key: int(value) for key, value in match.groupdict().items()}


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.glob(pattern))


def collect_artifact_counts(data_dir: Path) -> dict[str, int]:
    summarized_errors = _count_files(data_dir / 'summarized', '*_error.json')
    verified_errors = _count_files(data_dir / 'verified', '*_error.json')
    summarized_total = _count_files(data_dir / 'summarized', '*.json')
    verified_total = _count_files(data_dir / 'verified', '*.json')
    return {
        'raw': _count_files(data_dir / 'raw', '*.txt'),
        'json': _count_files(data_dir / 'json', '*.json'),
        'scored': _count_files(data_dir / 'scored', '*.json'),
        'summarized': max(0, summarized_total - summarized_errors),
        'summarized_errors': summarized_errors,
        'verified': max(0, verified_total - verified_errors),
        'verified_errors': verified_errors,
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
    return payload


def _clear_category_map(repo_root: Path) -> None:
    category_map_path = repo_root / 'apps' / 'summarizer' / 'data' / 'category_map.json'
    if category_map_path.exists():
        category_map_path.unlink()


def write_run_report(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def run_pipeline_job(
    *,
    repo_root: Path = REPO_ROOT,
    data_dir: Path = DATA_DIR,
    report_path: Path = REPORT_PATH,
    source: str,
    query: str,
    count: int,
    runner: Runner = run_command,
) -> dict[str, object]:
    started_at = time.strftime('%Y-%m-%dT%H:%M:%S%z')
    steps_payload: list[dict[str, object]] = []
    import_stats = {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    status = 'success'
    failed_step: str | None = None

    for step_name, command, cwd, env in _pipeline_steps(repo_root, source=source, query=query, count=count):
        result = runner(step_name, command, cwd, env)
        steps_payload.append(_serialize_step(result))
        if step_name == 'export_raw' and result.status == 'success':
            _clear_category_map(repo_root)
        if step_name == 'import':
            import_stats = parse_import_stats(result.stdout)
        if result.status != 'success':
            status = 'failed'
            failed_step = step_name
            break

    payload: dict[str, object] = {
        'status': status,
        'failed_step': failed_step,
        'started_at': started_at,
        'finished_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
        'source': source,
        'query': query,
        'count': count,
        'steps': steps_payload,
        'artifact_counts': collect_artifact_counts(data_dir),
        'import_stats': import_stats,
        'report_path': str(report_path),
    }
    write_run_report(report_path, payload)
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
