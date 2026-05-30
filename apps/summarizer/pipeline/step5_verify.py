"""
Step 5: 요약 → 할루시네이션 검증 (gemma4:e4b)
data/verified/{id}.json 저장
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pipeline.common import (
    JSON_DIR, SUMMARIZED_DIR, VERIFIED_DIR,
    call_llm, parse_json_response, save_json, load_json
)

SYSTEM = """당신은 팩트체크 전문가입니다. 뉴스 기사 원문과 요약문을 비교하여
요약문에서 사실이 틀리거나 왜곡된 내용을 찾아냅니다.

규칙:
- 표현이 달라도 사실이 일치하면 할루시네이션이 아닙니다.
  예) 원문 "이 대통령" → 요약 "이재명 대통령": 문맥상 동일 인물이면 정상.
- 수치·날짜·인물·기관이 원문과 다르게 기술된 경우만 할루시네이션입니다.
- 원문에 없는 사실(새로운 사건, 없는 수치 등)을 추가한 경우만 할루시네이션입니다.
- 원문 제목과 본문이 다루는 핵심 사건·주제와 요약문의 핵심 사건·주제가 다르면 suspicious입니다.
- 본문 안의 관련기사·페이지 잡음·다른 사건을 요약했거나, 제목의 주제를 뒤쪽에 끼워 넣고 실제 요약은 다른 사건을 중심으로 쓰면 suspicious입니다.
- 판정 전에 내부적으로 다음 순서로 확인하세요: (1) 원문 제목의 핵심 주제, (2) 본문이 실제로 다루는 중심 사건, (3) 요약문 중심 사건, (4) 셋이 같은 사건인지. 이 검토 과정은 출력하지 마세요.

판정 예시:
- 원문 제목: "농구 허웅 전 연인 명예훼손 재판" / 요약: "무인창고 현금 68억 은닉 수사" 중심 → 제목 주제를 뒤쪽에 끼워 넣었더라도 중심 사건이 다르므로 suspicious.
- 원문 제목: "세계 유일 유엔묘지…부산의 도전" / 요약: "부산 피란수도 유산 11곳, 세계유산 등재 도전" 중심 → 표현과 단어가 달라도 같은 부산 세계유산 등재 주제이므로 clean.
- 원문 제목: "보은서 김용식배 축구대회" / 요약: "보은군 4개 축구장에서 김용식배 축구대회 개최" 중심 → 조사·복합어 차이가 있어도 같은 대회 주제이므로 clean.
- 반드시 JSON으로만 응답하세요:

{
  \"verdict\": \"clean\" 또는 \"suspicious\",
  \"hallucinations\": [\"사실 오류 내용1\", \"사실 오류 내용2\"],
  \"confidence\": 0~100 (검증 신뢰도)
}"""


def process_file(article_id: str) -> dict | None:
    json_path = JSON_DIR / f"{article_id}.json"
    sum_path = SUMMARIZED_DIR / f"{article_id}.json"
    out_path = VERIFIED_DIR / f"{article_id}.json"

    if out_path.exists():
        return None
    if not json_path.exists() or not sum_path.exists():
        return None

    article = load_json(json_path)
    summary = load_json(sum_path)

    if "error" in article or "error" in summary:
        return None

    summary_text = "\n".join([
        f"headline_34: {summary.get('headline_34','')}",
        f"headline_58: {summary.get('headline_58','')}",
        f"headline_89: {summary.get('headline_89','')}",
        f"summary: {summary.get('summary','')}",
    ])

    user_prompt = (
        f"[원문]\n제목: {article.get('title','')}\n"
        f"본문: {article.get('content','')}\n\n"
        f"[요약문]\n{summary_text}\n\n"
        "요약문에서 원문에 없는 내용을 찾아주세요.\n"
        "주의: 원문 전체를 충분히 확인하세요. 원문 하단부에 있는 내용도 반드시 확인해야 합니다."
    )

    try:
        response = call_llm(SYSTEM, user_prompt, temperature=0.1, timeout=300)
        result = parse_json_response(response)
        result["_article_id"] = article_id
        result["_title"] = article.get("title", "")
        save_json(out_path, result)
        return result
    except Exception as e:
        save_json(VERIFIED_DIR / f"{article_id}_error.json", {"error": str(e)})
        return None


def _process_with_timing(article_id: str) -> tuple[str, dict | None, float]:
    t0 = time.time()
    result = process_file(article_id)
    elapsed = time.time() - t0
    return article_id, result, elapsed


def _summary_files() -> list[Path]:
    return sorted(f for f in SUMMARIZED_DIR.glob("*.json") if not f.name.endswith("_error.json"))


def main():
    VERIFIED_DIR.mkdir(parents=True, exist_ok=True)
    sum_files = _summary_files()
    max_workers = max(1, int(os.getenv("PIPELINE_MAX_WORKERS", "1")))

    if not sum_files:
        print("data/summarized/ 에 파일 없음.")
        return

    print(f"Step 5: 할루시네이션 검증 ({len(sum_files)}개, workers={max_workers})\n")
    clean, suspicious, fail = 0, 0, 0

    if max_workers == 1:
        for i, path in enumerate(sum_files, 1):
            article_id = path.stem
            print(f"[{i}/{len(sum_files)}] {article_id}", end="  ")
            _, result, elapsed = _process_with_timing(article_id)
            if result:
                verdict = result.get("verdict", "unknown")
                items = result.get("hallucinations", [])
                if verdict == "clean":
                    print(f"🟢 clean ({elapsed:.1f}s)")
                    clean += 1
                else:
                    print(f"🔴 suspicious: {items[:1]} ({elapsed:.1f}s)")
                    suspicious += 1
            else:
                print(f"⏭  ({elapsed:.1f}s)")
                fail += 1
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_process_with_timing, path.stem): path.stem for path in sum_files}
            done_count = 0
            for fut in as_completed(futures):
                article_id, result, elapsed = fut.result()
                done_count += 1
                print(f"[{done_count}/{len(sum_files)}] {article_id}", end="  ")
                if result:
                    verdict = result.get("verdict", "unknown")
                    items = result.get("hallucinations", [])
                    if verdict == "clean":
                        print(f"🟢 clean ({elapsed:.1f}s)")
                        clean += 1
                    else:
                        print(f"🔴 suspicious: {items[:1]} ({elapsed:.1f}s)")
                        suspicious += 1
                else:
                    print(f"⏭  ({elapsed:.1f}s)")
                    fail += 1

    print(f"\n완료: 🟢 clean {clean}개 / 🔴 suspicious {suspicious}개 / 실패 {fail}개")


if __name__ == "__main__":
    main()
