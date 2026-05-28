"""
파이프라인 실행 스크립트

사용법:
  python3 run_pipeline.py          # 전체 실행
  python3 run_pipeline.py --step 1 # 특정 스텝만 실행
  python3 run_pipeline.py --from 3 # 특정 스텝부터 실행
"""

import json
import sys
from pathlib import Path

STEPS = {
    1: ("scrape",    "pipeline.step1_scrape"),
    2: ("to_json",   "pipeline.step2_to_json"),
    3: ("score",     "pipeline.step3_score"),
    4: ("summarize", "pipeline.step4_summarize"),
    5: ("verify",    "pipeline.step5_verify"),
}
DATA_DIR = Path(__file__).resolve().parent / 'data'
RUN_MANIFEST_PATH = DATA_DIR / 'run_manifest.json'
STEP_OUTPUTS = {
    1: ('raw',),
    2: ('json',),
    3: ('scored',),
    4: ('summarized',),
    5: ('verified',),
}
ROOT_OUTPUTS_BY_STEP = {
    1: ('category_map.json', 'run_report.json'),
    2: ('category_map.json',),
}


def _remove_directory_files(directory: Path) -> None:
    if not directory.exists():
        return
    for path in directory.iterdir():
        if path.is_file():
            path.unlink()


def _prepare_pipeline_run(*, start_step: int) -> None:
    for step, directories in STEP_OUTPUTS.items():
        if step < start_step:
            continue
        for directory in directories:
            _remove_directory_files(DATA_DIR / directory)
    for step, filenames in ROOT_OUTPUTS_BY_STEP.items():
        if step < start_step:
            continue
        for filename in filenames:
            (DATA_DIR / filename).unlink(missing_ok=True)
    _write_run_manifest(complete=False)


def run_step(step_num: int):
    name, module_path = STEPS[step_num]
    print(f"\n{'='*60}")
    print(f"  Step {step_num}: {name}")
    print(f"{'='*60}")
    import importlib
    mod = importlib.import_module(module_path)
    mod.main()


def _raw_article_ids() -> list[str]:
    raw_dir = DATA_DIR / 'raw'
    if not raw_dir.exists():
        return []
    return sorted(path.stem for path in raw_dir.glob('*.txt'))


def _write_run_manifest(*, complete: bool) -> None:
    RUN_MANIFEST_PATH.write_text(
        json.dumps({'article_ids': _raw_article_ids(), 'complete': complete}, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def main():
    args = sys.argv[1:]

    if "--step" in args:
        idx = args.index("--step")
        step = int(args[idx + 1])
        _prepare_pipeline_run(start_step=step)
        run_step(step)

    elif "--from" in args:
        idx = args.index("--from")
        start = int(args[idx + 1])
        _prepare_pipeline_run(start_step=start)
        for s in range(start, 6):
            run_step(s)

    else:
        _prepare_pipeline_run(start_step=1)
        for s in STEPS:
            run_step(s)

    _write_run_manifest(complete=True)
    print("\n\n파이프라인 완료. 평가 리포트를 보려면:")
    print("  python3 evaluate.py")


if __name__ == "__main__":
    main()
