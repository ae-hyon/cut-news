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
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
JSON_DIR = ROOT / "apps" / "summarizer" / "data" / "json"
OUT = ROOT / ".dev" / "news-pipeline-fixed-variant-eval.json"


def _article_files(limit: int) -> list[Path]:
    return sorted(p for p in JSON_DIR.glob("*.json") if not p.name.endswith("_error.json"))[:limit]


def _run_variant(name: str, env_overrides: dict[str, str], files: list[Path]) -> dict[str, Any]:
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
        "name": name,
        "env": env_overrides,
        "returncode": proc.returncode,
        "elapsed_seconds": round(elapsed, 2),
    }
    if proc.returncode == 0:
        result.update(json.loads(proc.stdout.strip().splitlines()[-1]))
    else:
        result["stdout_tail"] = proc.stdout[-1000:]
        result["stderr_tail"] = proc.stderr[-1000:]
    return result


def main() -> int:
    files = _article_files(limit=int(os.environ.get("EVAL_ARTICLE_LIMIT", "3")))
    if not files:
        raise SystemExit("no fixed article JSON files found")
    variants = [
        (
            "hermes-default-profile",
            {
                "PIPELINE_LLM_BACKEND": "hermes_cli",
                "PIPELINE_HERMES_PROFILE": "cut-news-pipeline",
                "PIPELINE_HERMES_MODEL": "",
                "PIPELINE_HERMES_PROVIDER": "",
            },
        ),
        (
            "hermes-explicit-current",
            {
                "PIPELINE_LLM_BACKEND": "hermes_cli",
                "PIPELINE_HERMES_PROFILE": "cut-news-pipeline",
                "PIPELINE_HERMES_MODEL": "gpt-5.5",
                "PIPELINE_HERMES_PROVIDER": "openai-codex",
            },
        ),
        (
            "codex-low-auth-smoke",
            {
                "PIPELINE_LLM_BACKEND": "codex_exec",
                "PIPELINE_MODEL": "gpt-5.4-mini",
                "PIPELINE_CODEX_REASONING_EFFORT": "low",
                "PIPELINE_CODEX_MAX_ATTEMPTS": "1",
            },
        ),
    ]
    report = {
        "article_files": [p.name for p in files],
        "variants": [_run_variant(name, env, files) for name, env in variants],
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(v["returncode"] == 0 for v in report["variants"][:2]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
