import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import evaluate


def _write_summary(path: Path, article_id: str, h34_len: int, h58_len: int, h89_len: int):
    path.write_text(
        json.dumps(
            {
                "headline_34": "가" * h34_len,
                "headline_58": "나" * h58_len,
                "headline_89": "다" * h89_len,
                "summary": "요약 본문입니다.",
                "_title": f"기사 {article_id}",
                "_violations": [],
                "_headline_34_len": h34_len,
                "_headline_58_len": h58_len,
                "_headline_89_len": h89_len,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_evaluate_step4_returns_proximity_metrics_and_markdown(tmp_path, monkeypatch):
    summarized_dir = tmp_path / "summarized"
    summarized_dir.mkdir()

    _write_summary(summarized_dir / "001.json", "001", h34_len=34, h58_len=58, h89_len=89)
    _write_summary(summarized_dir / "002.json", "002", h34_len=32, h58_len=56, h89_len=85)
    _write_summary(summarized_dir / "003.json", "003", h34_len=30, h58_len=54, h89_len=86)

    monkeypatch.setattr(evaluate, "SUMMARIZED_DIR", summarized_dir)

    step4 = evaluate.evaluate_step4()

    assert step4["headline_proximity"]["headline_34"] == {
        "target": 34,
        "exact_target": 1,
        "within_2": 2,
        "within_4": 3,
    }
    assert step4["headline_proximity"]["headline_58"] == {
        "target": 58,
        "exact_target": 1,
        "within_2": 2,
        "within_4": 3,
    }
    assert step4["headline_proximity"]["headline_89"] == {
        "target": 89,
        "exact_target": 1,
        "within_2": 1,
        "within_4": 3,
    }

    markdown = evaluate.write_markdown_report(
        {"total": 0, "ok": 0, "ok_rate": "0%", "avg_content_len": 0},
        {"valid": 0, "total": 0, "avg_score": 0, "min_score": 0, "max_score": 0, "distribution": {}},
        step4,
        {"clean": 0, "clean_rate": "0%", "suspicious": 0, "suspicious_items": []},
    )

    assert "headline 목표 근접도" in markdown
    assert "h34 target=34 exact=1 ±2=2 ±4=3" in markdown
    assert "h58 target=58 exact=1 ±2=2 ±4=3" in markdown
    assert "h89 target=89 exact=1 ±2=1 ±4=3" in markdown
