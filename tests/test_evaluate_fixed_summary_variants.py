import importlib.util
import json
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate-fixed-summary-variants.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("evaluate_fixed_summary_variants", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_variants_json_uses_explicit_matrix(monkeypatch):
    module = _load_module()
    variants = [
        {
            "name": "hermes-gpt-5.5",
            "env": {
                "PIPELINE_LLM_BACKEND": "hermes_cli",
                "PIPELINE_HERMES_PROVIDER": "openai-codex",
                "PIPELINE_HERMES_MODEL": "gpt-5.5",
            },
        },
        {
            "name": "hermes-mini-high",
            "env": {
                "PIPELINE_LLM_BACKEND": "hermes_cli",
                "PIPELINE_HERMES_PROVIDER": "openai-codex",
                "PIPELINE_HERMES_MODEL": "gpt-5.4-mini",
                "PIPELINE_HERMES_REASONING_EFFORT": "high",
            },
        },
    ]
    monkeypatch.setenv("EVAL_VARIANTS_JSON", json.dumps(variants))

    parsed = module._variants_from_env()

    assert parsed == [(item["name"], item["env"]) for item in variants]


def test_default_variants_use_hermes_openai_codex_only():
    module = _load_module()

    variants = module._default_variants()

    assert variants
    for _name, env in variants:
        assert env["PIPELINE_LLM_BACKEND"] == "hermes_cli"
        assert env["PIPELINE_HERMES_PROVIDER"] == "openai-codex"
        assert "PIPELINE_HERMES_REASONING_EFFORT" in env
        assert "PIPELINE_CODEX_REASONING_EFFORT" not in env


def test_aggregate_variant_scores_penalizes_failures_and_length_violations():
    module = _load_module()
    passing = {
        "name": "passing",
        "returncode": 0,
        "elapsed_seconds": 12.0,
        "runs": [
            {
                "results": [
                    {"violations": [], "summary_chars": 120},
                    {"violations": [], "summary_chars": 130},
                ]
            },
            {
                "results": [
                    {"violations": [], "summary_chars": 115},
                    {"violations": [], "summary_chars": 125},
                ]
            },
        ],
    }
    weak = {
        "name": "weak",
        "returncode": 1,
        "elapsed_seconds": 12.0,
        "runs": [
            {
                "results": [
                    {"violations": ["headline_58 too long"], "summary_chars": 30},
                    {"violations": [], "summary_chars": 260},
                ]
            }
        ],
    }

    passing_metrics = module._aggregate_variant(passing)
    weak_metrics = module._aggregate_variant(weak)

    assert passing_metrics["success_rate"] == 1.0
    assert passing_metrics["length_violation_count"] == 0
    assert passing_metrics["score"] > weak_metrics["score"]


def test_rank_variants_orders_by_score_descending():
    module = _load_module()
    report = {
        "variants": [
            {"name": "bad", "aggregate": {"score": 10}},
            {"name": "good", "aggregate": {"score": 95}},
        ]
    }

    ranking = module._rank_variants(report)

    assert [item["name"] for item in ranking] == ["good", "bad"]
