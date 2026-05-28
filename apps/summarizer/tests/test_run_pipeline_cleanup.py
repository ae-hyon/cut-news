from __future__ import annotations

from pathlib import Path

import run_pipeline


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('payload', encoding='utf-8')


def test_prepare_full_run_removes_stale_pipeline_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_pipeline, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(run_pipeline, 'RUN_MANIFEST_PATH', tmp_path / 'run_manifest.json')
    for directory in ['raw', 'json', 'scored', 'summarized', 'verified']:
        _write(tmp_path / directory / 'stale.json')
    _write(tmp_path / 'category_map.json')
    _write(tmp_path / 'run_report.json')

    run_pipeline._prepare_pipeline_run(start_step=1)

    for directory in ['raw', 'json', 'scored', 'summarized', 'verified']:
        assert not (tmp_path / directory / 'stale.json').exists()
    assert not (tmp_path / 'category_map.json').exists()
    assert not (tmp_path / 'run_report.json').exists()
    assert (tmp_path / 'run_manifest.json').read_text(encoding='utf-8')


def test_prepare_partial_run_removes_only_downstream_artifacts(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(run_pipeline, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(run_pipeline, 'RUN_MANIFEST_PATH', tmp_path / 'run_manifest.json')
    for directory in ['raw', 'json', 'scored', 'summarized', 'verified']:
        _write(tmp_path / directory / 'stale.json')

    run_pipeline._prepare_pipeline_run(start_step=3)

    assert (tmp_path / 'raw' / 'stale.json').exists()
    assert (tmp_path / 'json' / 'stale.json').exists()
    for directory in ['scored', 'summarized', 'verified']:
        assert not (tmp_path / directory / 'stale.json').exists()
