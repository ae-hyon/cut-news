#!/usr/bin/env python3
"""Evaluate summary LLM variants on a fixed Cut News artifact subset.

This is intentionally lightweight: it calls the Step 4 summarizer prompt for a
stable subset of existing JSON artifacts and records parse/length outcomes. It
does not mutate pipeline output directories or import into the DB.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "apps" / "summarizer" / "data" / "json"
OUT = ROOT / ".dev" / "news-pipeline-fixed-variant-eval.json"


def _article_files(limit: int) -> list[Path]:
    return sorted(p for p in JSON_DIR.glob("*.json") if not p.name.endswith("_error.json"))[:limit]


def _default_variants() -> list[tuple[str, dict[str, str]]]:
    models = ["gpt-5.5", "gpt-5.4-mini"]
    efforts = ["low", "medium", "high"]
    variants: list[tuple[str, dict[str, str]]] = []
    for model in models:
        for effort in efforts:
            variants.append(
                (
                    f"hermes-openai-codex-{model}-{effort}",
                    {
                        "PIPELINE_LLM_BACKEND": "hermes_cli",
                        "PIPELINE_HERMES_PROFILE": "cut-news-pipeline",
                        "PIPELINE_HERMES_MODEL": model,
                        "PIPELINE_HERMES_PROVIDER": "openai-codex",
                        "PIPELINE_HERMES_REASONING_EFFORT": effort,
                    },
                )
            )
    return variants


def _variants_from_env() -> list[tuple[str, dict[str, str]]]:
    raw = os.environ.get("EVAL_VARIANTS_JSON")
    if not raw:
        return _default_variants()
    decoded = json.loads(raw)
    variants: list[tuple[str, dict[str, str]]] = []
    for index, item in enumerate(decoded, start=1):
        name = item.get("name") or f"variant-{index}"
        env = item.get("env") or {}
        if not isinstance(env, dict):
            raise SystemExit(f"variant {name!r} env must be an object")
        variants.append((str(name), {str(k): str(v) for k, v in env.items()}))
    if not variants:
        raise SystemExit("EVAL_VARIANTS_JSON must contain at least one variant")
    return variants


def _run_variant_once(env_overrides: dict[str, str], files: list[Path]) -> dict[str, Any]:
    code = r'''
import json
import time
from pathlib import Path
from pipeline.step4_summarize import SYSTEM, _build_initial_prompt, _compute_length_violations, _normalize_result_texts
from pipeline.common import call_llm, parse_json_response
files = json.loads(__import__('os').environ['EVAL_FILES'])
results=[]
for file_name in files:
    article = json.loads(Path(file_name).read_text(encoding='utf-8'))
    t0=time.time()
    raw = call_llm(SYSTEM, _build_initial_prompt(article), temperature=0.2, timeout=300)
    elapsed=time.time()-t0
    parsed = parse_json_response(raw)
    _normalize_result_texts(parsed)
    violations = _compute_length_violations(parsed)
    results.append({
        'article_id': Path(file_name).stem,
        'title': article.get('title'),
        'elapsed_seconds': round(elapsed, 2),
        'headline_lengths': {
            'headline_34': parsed.get('_headline_34_len'),
            'headline_58': parsed.get('_headline_58_len'),
            'headline_89': parsed.get('_headline_89_len'),
        },
        'violations': violations,
        'headline_34': parsed.get('headline_34'),
        'headline_58': parsed.get('headline_58'),
        'headline_89': parsed.get('headline_89'),
        'summary': parsed.get('summary'),
        'summary_chars': len(parsed.get('summary') or ''),
    })
print(json.dumps({'results': results}, ensure_ascii=False))
'''
    env = os.environ.copy()
    env.update(env_overrides)
    env["EVAL_FILES"] = json.dumps([str(p) for p in files])
    env.setdefault("HOME", "/Users/reddit")
    started = time.time()
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT / "apps" / "summarizer"),
        env=env,
        text=True,
        capture_output=True,
        timeout=900,
    )
    elapsed = time.time() - started
    result: dict[str, Any] = {
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 2),
    }
    if proc.returncode == 0:
        result.update(json.loads(proc.stdout.strip().splitlines()[-1]))
    else:
        result["stdout_tail"] = proc.stdout[-1000:]
        result["stderr_tail"] = proc.stderr[-1000:]
    return result


def _refresh_variant_result(result: dict[str, Any], repeat_count: int) -> None:
    runs = result.get("runs") or []
    result["returncode"] = 0 if runs and all(run["returncode"] == 0 for run in runs) else 1
    result["elapsed_seconds"] = round(sum(float(run["elapsed_seconds"]) for run in runs), 2)
    if repeat_count == 1 and runs:
        result.update(runs[0])
        result["name"] = result["name"]
        result["env"] = result["env"]
        result["runs"] = runs
    result["aggregate"] = _aggregate_variant(result)


def _run_variant(
    name: str,
    env_overrides: dict[str, str],
    files: list[Path],
    repeat_count: int,
    checkpoint: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": name,
        "env": env_overrides,
        "returncode": 1,
        "elapsed_seconds": 0.0,
        "runs": [],
    }
    for repeat_index in range(1, repeat_count + 1):
        run = _run_variant_once(env_overrides, files)
        run["repeat_index"] = repeat_index
        result["runs"].append(run)
        _refresh_variant_result(result, repeat_count)
        if checkpoint:
            checkpoint(result)
    return result


def _aggregate_variant(variant: dict[str, Any]) -> dict[str, Any]:
    runs = variant.get("runs") or []
    run_count = len(runs)
    success_count = sum(
        1
        for run in runs
        if run.get("returncode", 0 if run.get("results") else 1) == 0
    )
    results = [item for run in runs for item in run.get("results", [])]
    article_result_count = len(results)
    length_violation_count = sum(len(item.get("violations") or []) for item in results)
    summary_length_penalty = sum(
        1
        for item in results
        if int(item.get("summary_chars") or 0) < 80 or int(item.get("summary_chars") or 0) > 180
    )
    success_rate = success_count / run_count if run_count else 0.0
    elapsed = float(variant.get("elapsed_seconds") or 0)
    avg_elapsed_seconds = round(elapsed / run_count, 2) if run_count else 0.0
    score = 100.0 * success_rate
    score -= length_violation_count * 10
    score -= summary_length_penalty * 3
    score -= min(avg_elapsed_seconds / 60, 10)
    if article_result_count == 0:
        score -= 50
    return {
        "run_count": run_count,
        "success_count": success_count,
        "success_rate": round(success_rate, 4),
        "article_result_count": article_result_count,
        "length_violation_count": length_violation_count,
        "summary_length_penalty_count": summary_length_penalty,
        "avg_elapsed_seconds": avg_elapsed_seconds,
        "score": round(max(score, 0.0), 4),
    }


def _rank_variants(report: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        (
            {"name": variant["name"], **variant.get("aggregate", {})}
            for variant in report.get("variants", [])
        ),
        key=lambda item: item.get("score", 0),
        reverse=True,
    )


def _write_report(report: dict[str, Any]) -> None:
    report["ranking"] = _rank_variants(report)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    files = _article_files(limit=int(os.environ.get("EVAL_ARTICLE_LIMIT", "3")))
    if not files:
        raise SystemExit("no fixed article JSON files found")
    repeat_count = max(1, int(os.environ.get("EVAL_REPEAT_COUNT", "1")))
    variants = _variants_from_env()
    report: dict[str, Any] = {
        "article_files": [p.name for p in files],
        "repeat_count": repeat_count,
        "variants": [],
        "ranking": [],
    }

    def checkpoint_variant(partial_variant: dict[str, Any]) -> None:
        snapshot = json.loads(json.dumps(partial_variant, ensure_ascii=False))
        for index, existing in enumerate(report["variants"]):
            if existing.get("name") == snapshot.get("name"):
                report["variants"][index] = snapshot
                break
        else:
            report["variants"].append(snapshot)
        _write_report(report)
        aggregate = snapshot.get("aggregate", {})
        print(
            f"checkpoint {snapshot.get('name')} "
            f"runs={aggregate.get('run_count', 0)}/{repeat_count} "
            f"score={aggregate.get('score', 0)}",
            flush=True,
        )

    for name, env in variants:
        _run_variant(name, env, files, repeat_count, checkpoint=checkpoint_variant)

    _write_report(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ranking"] and report["ranking"][0].get("success_rate", 0) > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
