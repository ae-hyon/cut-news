"""
Step 3: JSON → 중요도 점수 할당 (gemma4:e4b)
data/scored/{id}.json 저장

절대 평가 (0-100점): 기사 자체의 독자 가치 기준
"""

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pipeline.common import JSON_DIR, SCORED_DIR, call_llm, parse_json_response, save_json, load_json

SYSTEM = """당신은 뉴스 기사의 독자 가치를 평가하는 전문 에디터입니다.

기사를 읽고 독자에게 얼마나 가치 있는지 0~100점으로 절대 평가합니다.
다른 기사와 비교하지 말고, 이 기사 자체의 가치만 평가합니다.

평가 기준:
- 영향력 (30점): 얼마나 많은 독자에게 영향을 미치는가
- 시의성 (25점): 지금 알아야 할 중요한 사건인가
- 정보 완결성 (25점): 기사가 충분한 정보를 전달하는가
- 독자 관심도 (20점): 독자가 읽고 싶어할 가능성

아래 JSON 형식으로만 응답하세요:
{
  \"score\": 0~100 사이의 정수,
  \"reason\": \"50자 이내 한국어 평가 이유\",
  \"breakdown\": {
    \"영향력\": 0~30,
    \"시의성\": 0~25,
    \"정보완결성\": 0~25,
    \"독자관심도\": 0~20
  }
}"""


def process_file(json_path: Path) -> dict | None:
    article_id = json_path.stem
    out_path = SCORED_DIR / f"{article_id}.json"

    if out_path.exists():
        print(f"  ⏭  {article_id} 스킵 (이미 존재)")
        return None

    article = load_json(json_path)
    if "error" in article:
        print(f"  ⚠️  {article_id} 에러 파일 스킵")
        return None

    user_prompt = (
        f"제목: {article.get('title','')}\n"
        f"날짜: {article.get('date','')}\n"
        f"본문: {article.get('content','')[:1500]}"
    )

    try:
        response = call_llm(SYSTEM, user_prompt, temperature=0.1, timeout=300)
        result = parse_json_response(response)
        result["_article_id"] = article_id
        result["_title"] = article.get("title", "")
        save_json(out_path, result)
        return result
    except Exception as e:
        save_json(SCORED_DIR / f"{article_id}_error.json", {"error": str(e), "_article_id": article_id})
        return None


def _process_with_timing(json_path: Path) -> tuple[Path, dict | None, float]:
    t0 = time.time()
    result = process_file(json_path)
    elapsed = time.time() - t0
    return json_path, result, elapsed


def main():
    SCORED_DIR.mkdir(parents=True, exist_ok=True)
    json_files = sorted(f for f in JSON_DIR.glob("[0-9]*.json") if "_error" not in f.name)
    max_workers = max(1, int(os.getenv("PIPELINE_MAX_WORKERS", "1")))

    if not json_files:
        print("data/json/ 에 파일 없음. step2_to_json.py 먼저 실행하세요.")
        return

    print(f"Step 3: 중요도 점수 할당 ({len(json_files)}개, workers={max_workers})\n")
    success, fail = 0, 0

    if max_workers == 1:
        for i, path in enumerate(json_files, 1):
            print(f"[{i}/{len(json_files)}] {path.name}", end="  ")
            _, result, elapsed = _process_with_timing(path)
            if result:
                score = result.get("score", "?")
                print(f"✅ 점수={score} ({elapsed:.1f}s)")
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
                    score = result.get("score", "?")
                    print(f"✅ 점수={score} ({elapsed:.1f}s)")
                    success += 1
                else:
                    print(f"⏭  ({elapsed:.1f}s)")
                    fail += 1

    print(f"\n완료: 성공 {success}개 / 실패 {fail}개 → data/scored/")


if __name__ == "__main__":
    main()
