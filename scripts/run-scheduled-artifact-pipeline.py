#!/usr/bin/env python3
"""Run the scheduled GitHub artifact -> summarizer/import -> report-check flow.

This is the operator-facing wrapper intended for cron/systemd/Hermes scheduled use.
It keeps the Codex OAuth HOME explicit, makes the target DATABASE_URL explicit to
subprocesses, and sends an optional failure notification after the report check.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
ROOT_ENV = ROOT / ".env"
DEFAULT_REPORT = ROOT / "apps" / "summarizer" / "data" / "run_report.json"
DEFAULT_HOME = "/Users/reddit"


@dataclass(frozen=True)
class CommandResult:
    name: str
    command: list[str]
    returncode: int
    stdout_tail: str
    stderr_tail: str


def read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_report(path: Path = DEFAULT_REPORT) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def redacted_database_label(database_url: str) -> str:
    if not database_url:
        return "missing"
    if "neon.tech" in database_url:
        return "neon"
    if database_url.startswith("sqlite"):
        return "sqlite"
    if database_url.startswith("postgresql"):
        return "postgresql"
    return database_url.split(":", 1)[0]


def tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def build_runtime_env(args: argparse.Namespace, base: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base if base is not None else os.environ)
    if args.load_dotenv:
        dotenv = read_env_file(args.dotenv_path)
        for key, value in dotenv.items():
            env.setdefault(key, value)
    if args.database_url:
        env["DATABASE_URL"] = args.database_url
    if not env.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required; export it explicitly or pass --load-dotenv/--database-url")

    env["HOME"] = args.home
    env.setdefault("PIPELINE_LLM_BACKEND", "codex_exec")
    env.setdefault("PIPELINE_MODEL", "gpt-5.4-mini")
    env.setdefault("PIPELINE_CODEX_REASONING_EFFORT", "low")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env["NEWS_PIPELINE_MAX_ARTICLES"] = str(args.max_articles) if args.max_articles else ""
    return env


def run_command(name: str, command: Sequence[str], env: Mapping[str, str]) -> CommandResult:
    completed = subprocess.run(command, cwd=ROOT, env=dict(env), text=True, capture_output=True)
    return CommandResult(
        name=name,
        command=list(command),
        returncode=completed.returncode,
        stdout_tail=tail(completed.stdout),
        stderr_tail=tail(completed.stderr),
    )


def alert_payload(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2)


def send_alert(summary: dict[str, Any], env: Mapping[str, str]) -> None:
    payload = alert_payload(summary)
    if command := env.get("PIPELINE_ALERT_COMMAND"):
        subprocess.run(command, cwd=ROOT, env=dict(env), input=payload, text=True, shell=True, check=False)
    if webhook_url := env.get("PIPELINE_ALERT_WEBHOOK_URL"):
        body = json.dumps({"text": payload}, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(webhook_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except Exception as exc:  # noqa: BLE001 - alert failure should not mask original run failure.
            print(f"warning: failed to send PIPELINE_ALERT_WEBHOOK_URL alert: {exc}", file=sys.stderr)


def run_scheduled_pipeline(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    env = build_runtime_env(args)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    commands: list[CommandResult] = []

    if args.dry_run:
        summary = {
            "status": "dry_run",
            "started_at": started_at,
            "home": env.get("HOME"),
            "database_target": redacted_database_label(env.get("DATABASE_URL", "")),
            "max_articles": args.max_articles,
            "commands": [
                "make local-pipeline-from-github",
                "make local-report-check REPORT_CHECK_ARGS=--require-uncapped",
            ],
        }
        return 0, summary

    pipeline = run_command("local-pipeline-from-github", ["make", "local-pipeline-from-github"], env)
    commands.append(pipeline)

    check_env = dict(env)
    check_env["REPORT_CHECK_ARGS"] = "--require-uncapped"
    report_check = run_command("local-report-check", ["make", "local-report-check"], check_env)
    commands.append(report_check)

    report = load_report(args.report)
    failed = any(result.returncode != 0 for result in commands)
    summary = {
        "status": "failed" if failed else "success",
        "started_at": started_at,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "home": env.get("HOME"),
        "database_target": redacted_database_label(env.get("DATABASE_URL", "")),
        "max_articles": args.max_articles,
        "report_path": str(args.report),
        "pipeline_status": report.get("status"),
        "failed_step": report.get("failed_step"),
        "feed_date": report.get("feed_date"),
        "import_stats": report.get("import_stats"),
        "drop_reason_counts": report.get("drop_reason_counts"),
        "snapshot_generation": report.get("snapshot_generation"),
        "commands": [result.__dict__ for result in commands],
    }
    if failed:
        send_alert(summary, env)
    return 1 if failed else 0, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run scheduled GitHub crawl artifact summarizer/import with report alerting")
    parser.add_argument("--home", default=DEFAULT_HOME, help="HOME used for Codex OAuth/session lookup")
    parser.add_argument("--database-url", help="explicit backend DATABASE_URL; preferred for schedulers")
    parser.add_argument("--load-dotenv", action="store_true", help="load missing values from repo root .env")
    parser.add_argument("--dotenv-path", type=Path, default=ROOT_ENV, help="dotenv path used with --load-dotenv")
    parser.add_argument("--max-articles", type=int, help="diagnostic cap; omit for product-like scheduled runs")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="pipeline run_report.json path")
    parser.add_argument("--dry-run", action="store_true", help="print resolved execution plan without running the pipeline")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.report.is_absolute():
        args.report = ROOT / args.report
    if not args.dotenv_path.is_absolute():
        args.dotenv_path = ROOT / args.dotenv_path
    code, summary = run_scheduled_pipeline(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
