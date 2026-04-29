"""
Step 4: JSON → 요약 (gemma4:e4b)
data/summarized/{id}.json 저장

요약 생성 후 인라인 할루시네이션 검증 → suspicious이면 피드백 포함 재생성 (최대 2회)
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pipeline.common import (
    JSON_DIR, SUMMARIZED_DIR, call_llm, parse_json_response, save_json, load_json
)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
with open(PROMPTS_DIR / "summarizer_system.md", encoding="utf-8") as f:
    SYSTEM = f.read()

VERIFY_SYSTEM = """당신은 팩트체크 전문가입니다. 뉴스 기사 원문과 요약문을 비교하여
요약문에서 사실이 틀리거나 왜곡된 내용을 찾아냅니다.

규칙:
- 표현이 달라도 사실이 일치하면 할루시네이션이 아닙니다.
  예) 원문 \"이 대통령\" → 요약 \"이재명 대통령\": 문맥상 동일 인물이면 정상.
- 수치·날짜·인물·기관이 원문과 다르게 기술된 경우만 할루시네이션입니다.
- 원문에 없는 사실(새로운 사건, 없는 수치 등)을 추가한 경우만 할루시네이션입니다.
- 반드시 JSON으로만 응답하세요:

{
  \"verdict\": \"clean\" 또는 \"suspicious\",
  \"hallucinations\": [\"사실 오류 내용1\", \"사실 오류 내용2\"],
  \"confidence\": 0~100 (검증 신뢰도)
}"""

PREFERRED_HEADLINE_FLOORS = {
    "headline_34": 31,
    "headline_58": 54,
    "headline_89": 82,
}


def _build_directional_fact_rules(article: dict) -> list[str]:
    text = f"{article.get('title', '')}\n{article.get('content', '')}"
    directional_markers = [
        "상승", "하락", "오름", "내림", "상승분", "반납", "마감", "종가", "장중", "등락", "WTI", "브렌트유", "달러-원", "환율", "유가",
    ]
    if not any(marker in text for marker in directional_markers):
        return []
    return [
        "가격·지수·환율·유가 기사에서는 상승/하락 방향, 변동률, 마감가를 원문과 다르게 바꾸지 마세요.",
        "장중 움직임과 최종 마감 결과를 혼동하지 말고, '상승분 반납' 같은 표현을 임의로 '상승'으로 바꾸지 마세요.",
    ]


def _build_initial_prompt(article: dict) -> str:
    extra_rules = [
        "반드시 원문에 있는 사실만 사용하세요.",
        "원문에 없는 해석, 배경 추론, 일반적 주의 문구를 추가하지 마세요.",
        "headline_34는 29~34자, headline_58는 50~58자, headline_89는 76~89자 범위를 반드시 지키세요.",
        "세 headline 모두 범위만 맞추지 말고 가능한 한 상한에 가깝게 채우세요.",
        "짧다고 느슨하게 끝내지 말고, 원문 사실을 더 넣어 의미 밀도를 높이세요.",
    ]

    title = article.get("title", "")
    content = article.get("content", "")

    if title.startswith("[인사]"):
        extra_rules.append(
            "인사 기사이므로 '재편', '정비', '마무리' 같은 해석 표현을 넣지 말고, 실제 인사 대상과 직책만 요약하세요."
        )
    if "풍랑주의보" in title or "풍랑주의보" in content:
        extra_rules.append(
            "기상 기사이므로 원문에 없는 '주의 필요', '안전 유의' 같은 상식적 권고를 추가하지 마세요."
        )
    extra_rules.extend(_build_directional_fact_rules(article))

    return (
        "다음 뉴스 기사를 요약해주세요.\n"
        "추가 규칙:\n- " + "\n- ".join(extra_rules) + "\n\n"
        f"{json.dumps(article, ensure_ascii=False, indent=2)}"
    )


def _build_length_retry_prompt(article: dict, result: dict, violations: list[str]) -> str:
    guidance = []
    for violation in violations:
        field = violation.split(":", 1)[0]
        current_len = result.get(f"_{field}_len", len(result.get(field, "")))
        if field == "headline_34":
            min_len, max_len = 29, 34
        elif field == "headline_58":
            min_len, max_len = 50, 58
        else:
            min_len, max_len = 76, 89
        if current_len < min_len:
            guidance.append(
                f"- {field}: 현재 {current_len}자입니다. 원문 사실을 1개 더 포함해 {max_len - 1}~{max_len}자에 가깝게 늘리세요. 군더더기 대신 구체 명사, 주체, 결과를 보강하세요."
            )
        elif current_len > max_len:
            guidance.append(
                f"- {field}: 현재 {current_len}자입니다. 핵심 사실은 유지하고 수식어를 줄여 {max_len - 1}~{max_len}자로 줄이세요."
            )
    guidance_text = "\n".join(guidance) if guidance else "- 세 headline 모두 요구 범위를 다시 정확히 맞추세요."
    return (
        "다음 뉴스 기사를 다시 요약해주세요.\n"
        "이전 응답은 headline 길이 목표를 정확히 맞추지 못했습니다.\n"
        "핵심 사실은 유지하되 원문 사실만 사용하세요.\n"
        "headline_34는 29~34자, headline_58는 50~58자, headline_89는 76~89자 범위를 반드시 맞추고, 가능하면 상한에 가깝게 채우세요.\n"
        "아래 지시를 그대로 반영하세요.\n"
        f"{guidance_text}\n"
        f"현재 위반: {violations}\n"
        f"이전 응답: {json.dumps(result, ensure_ascii=False)}\n\n"
        f"기사: {json.dumps(article, ensure_ascii=False, indent=2)}"
    )


def _build_density_retry_prompt(article: dict, result: dict) -> str | None:
    guidance = []
    for field, preferred_floor in PREFERRED_HEADLINE_FLOORS.items():
        current_len = result.get(f"_{field}_len", len(result.get(field, "")))
        if field == "headline_34":
            _, max_len = 29, 34
        elif field == "headline_58":
            _, max_len = 50, 58
        else:
            _, max_len = 76, 89
        if current_len < preferred_floor:
            guidance.append(
                f"- {field}: 현재 {current_len}자입니다. 범위는 맞더라도 아직 짧습니다. 원문 사실을 더 넣어 {preferred_floor}~{max_len}자 쪽으로 밀도 있게 늘리세요."
            )
    if not guidance:
        return None
    guidance_text = "\n".join(guidance)
    return (
        "다음 뉴스 기사를 다시 요약해주세요.\n"
        "이전 응답은 허용 범위 안이지만 headline 길이가 아직 너무 짧습니다.\n"
        "원문에 있는 사실만 사용해 더 구체적이고 밀도 있게 작성하세요.\n"
        "불필요한 수식어 대신 주체, 대상, 결과, 장소 같은 핵심 사실을 보강하세요.\n"
        f"{guidance_text}\n"
        f"이전 응답: {json.dumps(result, ensure_ascii=False)}\n\n"
        f"기사: {json.dumps(article, ensure_ascii=False, indent=2)}"
    )


def _can_attempt_final_underlength_rescue(violations: list[str]) -> bool:
    if not violations:
        return False
    for violation in violations:
        field, detail = violation.split(":", 1)
        if ">" in detail:
            return False
        current_len, min_len = detail.split("<", 1)
        if int(min_len) - int(current_len) > 8:
            return False
        if field not in {"headline_34", "headline_58", "headline_89"}:
            return False
    return True


def _build_final_underlength_rescue_prompt(article: dict, result: dict, violations: list[str]) -> str:
    guidance = []
    for violation in violations:
        field = violation.split(":", 1)[0]
        current_len = result.get(f"_{field}_len", len(result.get(field, "")))
        if field == "headline_34":
            min_len, max_len = 29, 34
        elif field == "headline_58":
            min_len, max_len = 50, 58
        else:
            min_len, max_len = 76, 89
        guidance.append(
            f"- {field}: 현재 {current_len}자입니다. 기존 의미는 유지하고 원문에 있는 주체·수치·대상 중 빠진 사실을 보강해 최소 {min_len}자, 가능하면 {max_len - 1}~{max_len}자로 맞추세요."
        )
    guidance_text = "\n".join(guidance)
    return (
        "다음 뉴스 기사를 다시 요약해주세요.\n"
        "이전 응답은 거의 맞았지만 일부 headline이 최소 글자 수에 몇 글자 부족합니다.\n"
        "이번에는 부족한 headline만 원문 사실로 조금 더 보강해 길이 계약을 정확히 맞추세요.\n"
        "절대 원문에 없는 해석이나 배경을 추가하지 말고, 이미 범위를 만족한 headline과 summary의 의미는 최대한 유지하세요.\n"
        f"{guidance_text}\n"
        f"현재 위반: {violations}\n"
        f"이전 응답: {json.dumps(result, ensure_ascii=False)}\n\n"
        f"기사: {json.dumps(article, ensure_ascii=False, indent=2)}"
    )


def _normalize_result_texts(result: dict) -> None:
    for field in ("headline_34", "headline_58", "headline_89", "summary"):
        value = result.get(field)
        if isinstance(value, str):
            result[field] = " ".join(value.split())


def _compute_length_violations(result: dict) -> list[str]:
    violations = []
    for field, (min_len, max_len) in {"headline_34": (29, 34), "headline_58": (50, 58), "headline_89": (76, 89)}.items():
        val = result.get(field, "")
        val_len = len(val)
        result[f"_{field}_len"] = val_len
        if val_len < min_len:
            violations.append(f"{field}:{val_len}<{min_len}")
        elif val_len > max_len:
            violations.append(f"{field}:{val_len}>{max_len}")
    result["_violations"] = violations
    return violations


def _repair_overlong_headlines(result: dict) -> list[str]:
    repaired_fields: list[str] = []
    for field, (_, max_len) in {"headline_34": (29, 34), "headline_58": (50, 58), "headline_89": (76, 89)}.items():
        value = result.get(field)
        if not isinstance(value, str):
            continue
        overflow = len(value) - max_len
        if overflow <= 0:
            continue
        if overflow > 5:
            continue
        trimmed = value[:max_len].rstrip(" ,·-—:;…")
        if len(trimmed) < max_len - 5:
            continue
        result[field] = trimmed
        repaired_fields.append(field)
    if repaired_fields:
        result["_auto_trimmed_fields"] = repaired_fields
    return repaired_fields


def _check_hallucination(article: dict, result: dict) -> dict:
    """요약 결과에 대해 할루시네이션 검증. verdict/hallucinations/confidence 반환."""
    summary_text = "\n".join([
        f"headline_34: {result.get('headline_34', '')}",
        f"headline_58: {result.get('headline_58', '')}",
        f"headline_89: {result.get('headline_89', '')}",
        f"summary: {result.get('summary', '')}",
    ])
    user_prompt = (
        f"[원문]\n제목: {article.get('title', '')}\n"
        f"본문: {article.get('content', '')[:2000]}\n\n"
        f"[요약문]\n{summary_text}\n\n"
        "요약문에서 원문에 없는 내용을 찾아주세요."
    )
    response = call_llm(VERIFY_SYSTEM, user_prompt, temperature=0.1, timeout=300)
    return parse_json_response(response)


def _build_retry_prompt(article: dict, hallucinations: list[str]) -> str:
    issues = "\n".join(f"- {h}" for h in hallucinations)
    extra_guidance = _build_directional_fact_rules(article)
    if any(keyword in issues for keyword in ["상승", "하락", "반납", "마감", "WTI", "유가", "환율"]):
        extra_guidance.append(
            "특히 방향·변동률·마감가 오류를 고치세요. 장중 고점/저점이나 상승분 반납을 최종 등락 방향으로 오해하면 안 됩니다."
        )
    guidance_block = ""
    if extra_guidance:
        guidance_block = "\n[추가 수정 지침]\n- " + "\n- ".join(extra_guidance)
    return (
        f"다음 뉴스 기사를 요약해주세요.\n\n"
        f"{json.dumps(article, ensure_ascii=False, indent=2)}\n\n"
        f"[이전 요약의 문제점 — 아래 내용은 원문에 없는 정보입니다. 반드시 제거하거나 수정하세요]\n"
        f"{issues}"
        f"{guidance_block}"
    )


def process_file(json_path: Path) -> dict | None:
    article_id = json_path.stem
    out_path = SUMMARIZED_DIR / f"{article_id}.json"

    if out_path.exists():
        print(f"  ⏭  {article_id} 스킵 (이미 존재)")
        return None

    article = load_json(json_path)
    if "error" in article:
        return None

    user_prompt = _build_initial_prompt(article)

    MAX_RETRIES = 2
    SKIP_INLINE_VERIFY = os.getenv("PIPELINE_SKIP_INLINE_VERIFY", "0") == "1"
    verdict_info = {}

    try:
        for attempt in range(MAX_RETRIES + 1):
            response = call_llm(SYSTEM, user_prompt, temperature=0.3, timeout=300)
            result = parse_json_response(response)
            _normalize_result_texts(result)

            # 글자 수 검증
            violations = _compute_length_violations(result)

            if violations and attempt < MAX_RETRIES:
                user_prompt = _build_length_retry_prompt(article, result, violations)
                continue

            if violations:
                repaired_fields = _repair_overlong_headlines(result)
                if repaired_fields:
                    violations = _compute_length_violations(result)

            if violations and attempt == MAX_RETRIES and _can_attempt_final_underlength_rescue(violations):
                rescue_prompt = _build_final_underlength_rescue_prompt(article, result, violations)
                rescue_response = call_llm(SYSTEM, rescue_prompt, temperature=0.2, timeout=300)
                result = parse_json_response(rescue_response)
                _normalize_result_texts(result)
                violations = _compute_length_violations(result)
                if violations:
                    repaired_fields = _repair_overlong_headlines(result)
                    if repaired_fields:
                        violations = _compute_length_violations(result)
                result["_final_length_rescue"] = True

            if violations:
                raise ValueError(
                    "Summary length contract violated after retries: "
                    + ", ".join(violations)
                )

            density_feedback = _build_density_retry_prompt(article, result)
            if density_feedback and attempt < MAX_RETRIES:
                user_prompt = density_feedback
                continue

            if SKIP_INLINE_VERIFY:
                verdict_info = {"verdict": "skipped", "hallucinations": [], "confidence": 0}
                break

            # 인라인 할루시네이션 검증
            try:
                verdict_info = _check_hallucination(article, result)
            except Exception:
                verdict_info = {"verdict": "unknown", "hallucinations": [], "confidence": 0}

            verdict = verdict_info.get("verdict", "unknown")
            hallucinations = verdict_info.get("hallucinations", [])

            if verdict != "suspicious" or attempt == MAX_RETRIES:
                break

            # suspicious → 피드백 포함 재시도
            user_prompt = _build_retry_prompt(article, hallucinations)

        result["_article_id"] = article_id
        result["_title"] = article.get("title", "")
        result["_verify"] = verdict_info
        result["_retry_count"] = attempt

        save_json(out_path, result)
        return result
    except Exception as e:
        save_json(SUMMARIZED_DIR / f"{article_id}_error.json", {"error": str(e), "_article_id": article_id})
        return None


def _process_with_timing(json_path: Path) -> tuple[Path, dict | None, float]:
    t0 = time.time()
    result = process_file(json_path)
    elapsed = time.time() - t0
    return json_path, result, elapsed


def main():
    SUMMARIZED_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(f for f in JSON_DIR.glob("[0-9]*.json") if "_error" not in f.name)
    max_workers = max(1, int(os.getenv("PIPELINE_MAX_WORKERS", "1")))

    if not json_files:
        print("data/json/ 에 파일 없음.")
        return

    print(f"Step 4: 요약 생성 ({len(json_files)}개, workers={max_workers})\n")
    success, fail = 0, 0

    if max_workers == 1:
        for i, path in enumerate(json_files, 1):
            print(f"[{i}/{len(json_files)}] {path.name}", end="  ")
            _, result, elapsed = _process_with_timing(path)
            if result:
                v = result.get("_violations", [])
                verdict = result.get("_verify", {}).get("verdict", "?")
                retries = result.get("_retry_count", 0)
                h34 = result.get("_headline_34_len", "?")
                verdict_icon = "🟢" if verdict == "clean" else ("🔴" if verdict == "suspicious" else "⬜")
                retry_str = f" retry={retries}" if retries else ""
                status = f"⚠️  {v}" if v else "✅"
                print(f"{status} h34={h34}자 {verdict_icon}{retry_str} ({elapsed:.1f}s)")
                success += 1
            else:
                print(f"⏭  ({elapsed:.1f}s)")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_process_with_timing, path): path for path in json_files}
            done_count = 0
            for fut in as_completed(futures):
                path, result, elapsed = fut.result()
                done_count += 1
                print(f"[{done_count}/{len(json_files)}] {path.name}", end="  ")
                if result:
                    v = result.get("_violations", [])
                    verdict = result.get("_verify", {}).get("verdict", "?")
                    retries = result.get("_retry_count", 0)
                    h34 = result.get("_headline_34_len", "?")
                    verdict_icon = "🟢" if verdict == "clean" else ("🔴" if verdict == "suspicious" else "⬜")
                    retry_str = f" retry={retries}" if retries else ""
                    status = f"⚠️  {v}" if v else "✅"
                    print(f"{status} h34={h34}자 {verdict_icon}{retry_str} ({elapsed:.1f}s)")
                    success += 1
                else:
                    print(f"⏭  ({elapsed:.1f}s)")
                    fail += 1

    print(f"\n완료: 성공 {success}개 / 실패 {fail}개 → data/summarized/")


if __name__ == "__main__":
    main()
