import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import step3_score, step4_summarize, step5_verify


def _write_json(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'ok': True}), encoding='utf-8')


def test_step3_selects_hash_article_ids_and_skips_error_files(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    _write_json(json_dir / '05d506932773.json')
    _write_json(json_dir / 'a6a3cbbe2ed1.json')
    _write_json(json_dir / 'a6a3cbbe2ed1_error.json')
    monkeypatch.setattr(step3_score, 'JSON_DIR', json_dir)

    assert [p.name for p in step3_score._input_json_files()] == [
        '05d506932773.json',
        'a6a3cbbe2ed1.json',
    ]


def test_step4_selects_hash_article_ids_and_skips_error_files(tmp_path, monkeypatch):
    json_dir = tmp_path / 'json'
    _write_json(json_dir / '15e31771bf18.json')
    _write_json(json_dir / 'cc5111b6fa91.json')
    _write_json(json_dir / 'cc5111b6fa91_error.json')
    monkeypatch.setattr(step4_summarize, 'JSON_DIR', json_dir)

    assert [p.name for p in step4_summarize._input_json_files()] == [
        '15e31771bf18.json',
        'cc5111b6fa91.json',
    ]


def test_step5_selects_hash_summary_ids_and_skips_error_files(tmp_path, monkeypatch):
    summarized_dir = tmp_path / 'summarized'
    _write_json(summarized_dir / '5199e600904a.json')
    _write_json(summarized_dir / 'f574bfb09212.json')
    _write_json(summarized_dir / 'f574bfb09212_error.json')
    monkeypatch.setattr(step5_verify, 'SUMMARIZED_DIR', summarized_dir)

    assert [p.name for p in step5_verify._summary_files()] == [
        '5199e600904a.json',
        'f574bfb09212.json',
    ]
