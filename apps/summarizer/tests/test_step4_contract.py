import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import step4_summarize


def test_process_file_writes_error_instead_of_saving_contract_violating_summary(tmp_path, monkeypatch):
    article_path = tmp_path / "009.json"
    article_path.write_text(
        json.dumps(
            {
                "title": "테스트 기사",
                "content": "이 기사는 요약 길이 계약 위반 저장 방지 테스트용 본문입니다.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summarized_dir = tmp_path / "summarized"
    monkeypatch.setattr(step4_summarize, "SUMMARIZED_DIR", summarized_dir)
    monkeypatch.setenv("PIPELINE_SKIP_INLINE_VERIFY", "1")

    violating_payload = json.dumps(
        {
            "headline_34": "너무 짧음",
            "headline_58": "이 헤드라인도 여전히 계약보다 짧습니다",
            "headline_89": "이 헤드라인 역시 최종 재시도 이후에도 최소 길이를 끝내 충족하지 못하도록 일부러 짧게 작성했습니다",
            "summary": "요약 본문",
        },
        ensure_ascii=False,
    )

    monkeypatch.setattr(step4_summarize, "call_llm", lambda *args, **kwargs: violating_payload)

    result = step4_summarize.process_file(article_path)

    assert result is None
    assert not (summarized_dir / "009.json").exists()

    error_path = summarized_dir / "009_error.json"
    assert error_path.exists()
    error_data = json.loads(error_path.read_text(encoding="utf-8"))
    assert error_data["_article_id"] == "009"
    assert "length contract" in error_data["error"]


def test_process_file_salvages_small_overflow_by_trimming_last_retry_result(tmp_path, monkeypatch):
    article_path = tmp_path / "010.json"
    article_path.write_text(
        json.dumps(
            {
                "title": "테스트 기사",
                "content": "이 기사는 마지막 재시도 결과가 몇 글자만 초과할 때 자동으로 잘라 저장하는지 확인합니다.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summarized_dir = tmp_path / "summarized"
    monkeypatch.setattr(step4_summarize, "SUMMARIZED_DIR", summarized_dir)
    monkeypatch.setenv("PIPELINE_SKIP_INLINE_VERIFY", "1")

    payload = json.dumps(
        {
            "headline_34": "가" * 35,
            "headline_58": "나" * 59,
            "headline_89": "다" * 92,
            "summary": "요약 본문",
        },
        ensure_ascii=False,
    )

    monkeypatch.setattr(step4_summarize, "call_llm", lambda *args, **kwargs: payload)

    result = step4_summarize.process_file(article_path)

    assert result is not None
    assert result["_auto_trimmed_fields"] == ["headline_34", "headline_58", "headline_89"]
    assert len(result["headline_34"]) == 34
    assert len(result["headline_58"]) == 58
    assert len(result["headline_89"]) == 89
    assert (summarized_dir / "010.json").exists()
