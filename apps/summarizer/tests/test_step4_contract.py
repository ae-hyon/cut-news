import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import step4_summarize
from pipeline.step4_summarize import _build_initial_prompt, _build_retry_prompt


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


def test_initial_prompt_adds_directional_fact_guard_for_market_articles():
    article = {
        "title": "미·이란 협상재개 기대에 국제유가 5일만에 하락…WTI 1.5%↓",
        "content": "WTI는 전장 대비 1.51% 내렸고 장초반 상승분을 반납했다.",
    }

    prompt = _build_initial_prompt(article)

    assert "상승/하락 방향, 변동률, 마감가를 원문과 다르게 바꾸지 마세요." in prompt
    assert "장중 움직임과 최종 마감 결과를 혼동하지 말고" in prompt


def test_retry_prompt_adds_directional_fact_fix_guidance_for_hallucination_feedback():
    article = {
        "title": "[뉴욕유가] 美·이란 2주만에 다시 협상 테이블로…WTI 5일만에 하락",
        "content": "WTI 가격은 전장 대비 1.51% 내렸고 장중 92.71달러까지 떨어졌다.",
    }

    prompt = _build_retry_prompt(article, ["headline_58의 'WTI는 장초반 상승분 1.5%↑를 반납'은 원문과 다릅니다."])

    assert "특히 방향·변동률·마감가 오류를 고치세요." in prompt
    assert "상승/하락 방향, 변동률, 마감가를 원문과 다르게 바꾸지 마세요." in prompt


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


def test_process_file_attempts_final_underlength_rescue_on_last_retry(tmp_path, monkeypatch):
    article_path = tmp_path / "011.json"
    article_path.write_text(
        json.dumps(
            {
                "title": "테스트 기사",
                "content": "이 기사는 마지막 재시도 뒤에도 몇 글자 부족한 headline을 한 번 더 구조화된 프롬프트로 복구하는지 확인합니다.",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summarized_dir = tmp_path / "summarized"
    monkeypatch.setattr(step4_summarize, "SUMMARIZED_DIR", summarized_dir)
    monkeypatch.setenv("PIPELINE_SKIP_INLINE_VERIFY", "1")

    first_payload = json.dumps(
        {
            "headline_34": "가" * 34,
            "headline_58": "나" * 46,
            "headline_89": "다" * 89,
            "summary": "요약 본문",
        },
        ensure_ascii=False,
    )
    rescued_payload = json.dumps(
        {
            "headline_34": "가" * 34,
            "headline_58": "나" * 55,
            "headline_89": "다" * 89,
            "summary": "요약 본문",
        },
        ensure_ascii=False,
    )

    responses = [first_payload, first_payload, first_payload, rescued_payload]

    def fake_call_llm(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(step4_summarize, "call_llm", fake_call_llm)

    result = step4_summarize.process_file(article_path)

    assert result is not None
    assert result["_final_length_rescue"] is True
    assert len(result["headline_58"]) == 55
    assert result["_retry_count"] == 2
    assert not (summarized_dir / "011_error.json").exists()
    assert (summarized_dir / "011.json").exists()
