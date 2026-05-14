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
    assert report['import_stats'] == {'inserted': 1, 'updated': 2, 'deleted': 0, 'skipped': 3}
    assert report['quality_gate_skip_counts'] == {'violations': 1}
    assert report['drop_reason_counts'] == {'category_unmapped': 2}
    assert report['classification_source_counts'] == {'source_subcategory': 1}
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
    persisted = json.loads(report_path.read_text(encoding='utf-8'))
    assert persisted['failed_step'] == 'summarize'
    archived_reports = list((data_dir / 'run_reports').glob('run_*.json'))
    assert len(archived_reports) == 1
    assert json.loads(archived_reports[0].read_text(encoding='utf-8'))['failed_step'] == 'summarize'
