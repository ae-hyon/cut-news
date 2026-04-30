from __future__ import annotations

import json
from pathlib import Path

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


def test_run_pipeline_job_writes_success_report_with_step_results(tmp_path: Path):
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
        if step_name == 'import':
            stdout = 'summarizer article import complete: inserted=1 updated=2 deleted=0 skipped=3\n'
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

    report = run_news_pipeline_job.run_pipeline_job(
        repo_root=tmp_path,
        data_dir=data_dir,
        report_path=report_path,
        source='seeded',
        query='경제',
        count=6,
        runner=fake_runner,
    )

    assert calls == ['collect', 'export_raw', 'summarize', 'import']
    assert report['status'] == 'success'
    assert report['failed_step'] is None
    assert report['artifact_counts']['raw'] == 1
    assert report['artifact_counts']['summarized'] == 1
    assert report['artifact_counts']['summarized_errors'] == 1
    assert report['artifact_counts']['verified'] == 1
    assert report['import_stats'] == {'inserted': 1, 'updated': 2, 'deleted': 0, 'skipped': 3}
    assert report_path.exists()
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    assert persisted['status'] == 'success'
    assert persisted['steps'][-1]['name'] == 'import'


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
    assert report['steps'][-1]['stderr'] == 'boom'
    assert report['import_stats'] == {'inserted': 0, 'updated': 0, 'deleted': 0, 'skipped': 0}
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    assert persisted['failed_step'] == 'summarize'
