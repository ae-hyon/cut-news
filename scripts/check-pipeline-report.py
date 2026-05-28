#!/usr/bin/env python3
"""Validate a Cut News pipeline run report for operational alerting.

The script prints a compact JSON summary and exits non-zero when the report
should page/fail an operator job.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "apps" / "summarizer" / "data" / "run_report.json"


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing pipeline report: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid pipeline report JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid pipeline report shape: expected object in {path}")
    return payload


def _counter(payload: dict[str, Any], section: str, key: str) -> int:
    value = payload.get(section)
    if not isinstance(value, dict):
        return 0
    raw = value.get(key, 0)
    return raw if isinstance(raw, int) else 0


def _has_positive_counter(payload: dict[str, Any], section: str) -> bool:
    value = payload.get(section)
    if not isinstance(value, dict):
        return False
    return any(isinstance(count, int) and count > 0 for count in value.values())


def evaluate_report(payload: dict[str, Any], *, require_uncapped: bool) -> tuple[list[str], dict[str, Any]]:
    import_inserted = _counter(payload, "import_stats", "inserted")
    import_updated = _counter(payload, "import_stats", "updated")
    usable_imports = import_inserted + import_updated
    snapshot_failed = _counter(payload, "snapshot_generation", "failed_count")
    snapshot_attempted = _counter(payload, "snapshot_generation", "attempted_user_count")
    keyword_rule_classifications = _counter(payload, "classification_source_counts", "keyword_rule")

    failures: list[str] = []
    quality_warnings: list[str] = []
    if payload.get("status") != "success":
        failures.append(f"status={payload.get('status')!r}")
    if payload.get("failed_step"):
        failures.append(f"failed_step={payload.get('failed_step')!r}")
    if usable_imports <= 0:
        failures.append("zero_usable_imports")
    if snapshot_failed > 0:
        failures.append(f"snapshot_generation.failed_count={snapshot_failed}")
    if require_uncapped and payload.get("max_articles") is not None:
        failures.append(f"max_articles={payload.get('max_articles')!r}")
    if usable_imports > 0 and keyword_rule_classifications == usable_imports:
        quality_warnings.append("all_classifications_from_keyword_rule")

    summary = {
        "status": payload.get("status"),
        "failed_step": payload.get("failed_step"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "feed_date": payload.get("feed_date"),
        "max_articles": payload.get("max_articles"),
        "crawl_input_path": payload.get("crawl_input_path"),
        "crawl_report_path": payload.get("crawl_report_path"),
        "import_inserted": import_inserted,
        "import_updated": import_updated,
        "usable_imports": usable_imports,
        "drop_reason_counts": payload.get("drop_reason_counts") or {},
        "has_drop_reasons": _has_positive_counter(payload, "drop_reason_counts"),
        "classification_source_counts": payload.get("classification_source_counts") or {},
        "quality_warnings": quality_warnings,
        "snapshot_attempted": snapshot_attempted,
        "snapshot_failed": snapshot_failed,
        "archive_report_path": payload.get("archive_report_path"),
        "failures": failures,
    }
    return failures, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate apps/summarizer/data/run_report.json for ops alerting")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="run_report.json path")
    parser.add_argument(
        "--require-uncapped",
        action="store_true",
        help="fail if NEWS_PIPELINE_MAX_ARTICLES was set; use for product-like scheduled runs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = _load_report(args.report if args.report.is_absolute() else ROOT / args.report)
    failures, summary = evaluate_report(report, require_uncapped=args.require_uncapped)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
