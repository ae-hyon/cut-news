#!/usr/bin/env python3
"""Download the latest GitHub Actions Naver crawl artifact for local pipeline use."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKFLOW = 'crawl-naver.yml'
DEFAULT_OUTPUT_DIR = ROOT / 'apps' / 'crawler' / 'output' / 'github-actions'


def run_gh(args: list[str]) -> str:
    completed = subprocess.run(['gh', *args], text=True, capture_output=True)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or 'gh command failed'
        raise SystemExit(detail)
    return completed.stdout


def default_repo() -> str:
    if repo := run_gh(['repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner']).strip():
        return repo
    raise SystemExit('could not determine GitHub repo; pass --repo owner/name')


def latest_successful_run(repo: str, workflow: str) -> str:
    output = run_gh([
        'run',
        'list',
        '--repo',
        repo,
        '--workflow',
        workflow,
        '--status',
        'success',
        '--limit',
        '1',
        '--json',
        'databaseId',
    ])
    runs = json.loads(output)
    if not runs:
        raise SystemExit(f'no successful {workflow} runs found in {repo}')
    return str(runs[0]['databaseId'])


def find_required_file(output_dir: Path, filename: str) -> Path:
    matches = sorted(output_dir.rglob(filename))
    if not matches:
        raise SystemExit(f'downloaded artifact is missing {filename} under {output_dir}')
    return matches[0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Download a GitHub Actions crawl artifact into apps/crawler/output/github-actions')
    parser.add_argument('--repo', help='GitHub repo in owner/name form; defaults to gh repo view')
    parser.add_argument('--workflow', default=DEFAULT_WORKFLOW, help='workflow file/name used to find the latest successful run')
    parser.add_argument('--run-id', help='specific GitHub Actions run ID; defaults to latest successful workflow run')
    parser.add_argument('--artifact-name', help='specific artifact name; defaults to naver-crawl-{run-id}')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT_DIR, help='directory to replace with downloaded artifact files')
    parser.add_argument('--keep-existing', action='store_true', help='do not remove output-dir before downloading')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo or default_repo()
    run_id = args.run_id or latest_successful_run(repo, args.workflow)
    artifact_name = args.artifact_name or f'naver-crawl-{run_id}'
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir

    if output_dir.exists() and not args.keep_existing:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_gh(['run', 'download', run_id, '--repo', repo, '--name', artifact_name, '--dir', str(output_dir)])

    latest = find_required_file(output_dir, 'latest.json')
    crawl_report = find_required_file(output_dir, 'crawl_report.json')
    summary = find_required_file(output_dir, 'github_action_crawl_summary.json')

    # Normalize paths so follow-up Make targets have stable locations regardless of artifact layout.
    for source, target in [
        (latest, output_dir / 'latest.json'),
        (crawl_report, output_dir / 'crawl_report.json'),
        (summary, output_dir / 'github_action_crawl_summary.json'),
    ]:
        if source != target:
            shutil.copy2(source, target)

    article_count = len(json.loads((output_dir / 'latest.json').read_text(encoding='utf-8')))
    print(json.dumps({
        'repo': repo,
        'run_id': run_id,
        'artifact_name': artifact_name,
        'output_dir': str(output_dir),
        'latest_json': str(output_dir / 'latest.json'),
        'crawl_report_json': str(output_dir / 'crawl_report.json'),
        'summary_json': str(output_dir / 'github_action_crawl_summary.json'),
        'article_count': article_count,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
