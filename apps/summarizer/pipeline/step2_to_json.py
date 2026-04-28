"""
Step 2: raw/*.txt → JSON 변환
data/json/{id}.json 저장

기본 경로는 LLM 파싱이고, 실패 시 연합뉴스 형식 원문을 규칙 기반으로 fallback 파싱한다.
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pipeline.common import RAW_DIR, JSON_DIR, call_llm, parse_json_response, save_json

SYSTEM = """뉴스 기사 텍스트를 파싱하여 구조화된 JSON으로 변환합니다.

입력은 다음 형식의 plain text입니다:
  제목: ...
  날짜: ...
  기자: ...
  URL: ...
  ---
  본문 내용

아래 JSON 형식으로만 응답하세요. 다른 텍스트는 절대 포함하지 마세요:
{
  \"title\": \"기사 제목\",
  \"date\": \"YYYY-MM-DD 형식으로 변환 (파악 불가 시 원문 그대로)\",
  \"author\": \"기자명 (없으면 빈 문자열)\",
  \"url\": \"기사 URL\",
  \"content\": \"본문 전체 (--- 이하 내용, 광고/저작권 문구 제외)\"
}"""


def _extract_header_value(raw_text: str, field: str) -> str:
    pattern = rf"^{re.escape(field)}:\s*(.*)$"
    m = re.search(pattern, raw_text, flags=re.MULTILINE)
    return m.group(1).strip() if m else ""


def _normalize_date(raw_date: str) -> str:
    m = re.search(r"(20\d{2})[년/-]?(\d{2})[월/-]?(\d{2})", raw_date)
    if not m:
        return raw_date.strip()
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _fallback_parse_yonhap(raw_text: str, source_name: str) -> dict:
    title = _extract_header_value(raw_text, "제목")
    raw_date = _extract_header_value(raw_text, "날짜")
    url = _extract_header_value(raw_text, "URL")

    parts = raw_text.split("---", 1)
    body_block = parts[1] if len(parts) == 2 else raw_text
    lines = [line.strip() for line in body_block.splitlines()]

    authors: list[str] = []
    for i, line in enumerate(lines[:14]):
        if line == "기자" and i > 0:
            prev = lines[i - 1].strip()
            if prev and prev not in authors and prev not in {"이전", "다음", "구독", "구독중"}:
                authors.append(prev)
    author = ", ".join(authors)

    content_lines: list[str] = []
    started = False
    stop_markers = (
        "제보는 카카오톡",
        "<저작권자",
        "무단 전재-재배포",
        "AI 학습 및 활용 금지",
    )
    skip_exact = {"기자", "구독", "구독중", "이전", "다음"}

    for line in lines:
        if not line:
            continue
        if any(marker in line for marker in stop_markers):
            break
        if re.fullmatch(r"20\d{2}[./년\-\s:월일]+(?:송고)?", line):
            break
        if re.match(r"^[\w.+-]+@[\w.-]+$", line):
            continue
        if line in skip_exact:
            continue
        if not started:
            if line.startswith("(") or line.startswith("[") or "=연합뉴스" in line:
                started = True
                content_lines.append(line)
            elif i := 0:
                pass
            else:
                if len(line) >= 12 and not re.fullmatch(r"[가-힣]{2,4}", line):
                    started = True
                    content_lines.append(line)
            continue
        content_lines.append(line)

    if not content_lines:
        cleaned = []
        for line in lines:
            if not line or line in skip_exact:
                continue
            if any(marker in line for marker in stop_markers):
                break
            if re.match(r"^[\w.+-]+@[\w.-]+$", line):
                continue
            if re.fullmatch(r"20\d{2}[./년\-\s:월일]+(?:송고)?", line):
                break
            cleaned.append(line)
        content_lines = cleaned

    content = "\n".join(content_lines).strip()
    return {
        "title": title,
        "date": _normalize_date(raw_date),
        "author": author,
        "url": url,
        "content": content,
        "_source_file": source_name,
    }


def process_file(raw_path: Path) -> tuple[str, dict | None]:
    article_id = raw_path.stem
    out_path = JSON_DIR / f"{article_id}.json"
    err_path = JSON_DIR / f"{article_id}_error.json"

    if out_path.exists():
        return "skipped", None

    raw_text = raw_path.read_text(encoding="utf-8")

    parts = raw_text.split("---", 1)
    if len(parts) == 2 and len(parts[1].strip()) < 200:
        return "skipped", None

    try:
        response = call_llm(SYSTEM, raw_text, temperature=0.1, timeout=300)
        result = parse_json_response(response)
        result["_source_file"] = raw_path.name
        save_json(out_path, result)
        if err_path.exists():
            err_path.unlink()
        return "success", result
    except Exception as e:
        try:
            fallback = _fallback_parse_yonhap(raw_text, raw_path.name)
            if fallback["title"] and fallback["url"] and fallback["content"]:
                save_json(out_path, fallback)
                if err_path.exists():
                    err_path.unlink()
                return "fallback", fallback
        except Exception:
            pass
        error = {"error": str(e), "_source_file": raw_path.name}
        save_json(err_path, error)
        return "failed", None


def _process_with_timing(raw_path: Path) -> tuple[Path, str, dict | None, float]:
    t0 = time.time()
    status, result = process_file(raw_path)
    elapsed = time.time() - t0
    return raw_path, status, result, elapsed


def main():
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = sorted(RAW_DIR.glob("*.txt"))
    max_workers = max(1, int(os.getenv("PIPELINE_MAX_WORKERS", "1")))

    if not raw_files:
        print("data/raw/ 에 파일 없음. step1_scrape.py 먼저 실행하세요.")
        return

    print(f"Step 2: raw→JSON 변환 ({len(raw_files)}개, workers={max_workers})\n")
    success, skipped, failed = 0, 0, 0

    def handle_result(index: int, total: int, path: Path, status: str, elapsed: float) -> None:
        nonlocal success, skipped, failed
        print(f"[{index}/{total}] {path.name}", end="  ")
        if status == "success":
            print(f"✅ ({elapsed:.1f}s)")
            success += 1
        elif status == "fallback":
            print(f"🛟 ({elapsed:.1f}s)")
            success += 1
        elif status == "skipped":
            print(f"⏭  ({elapsed:.1f}s)")
            skipped += 1
        else:
            print(f"❌ ({elapsed:.1f}s)")
            failed += 1

    if max_workers == 1:
        for i, path in enumerate(raw_files, 1):
            _, status, _, elapsed = _process_with_timing(path)
            handle_result(i, len(raw_files), path, status, elapsed)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_process_with_timing, path): path for path in raw_files}
            done_count = 0
            for fut in as_completed(futures):
                path, status, _, elapsed = fut.result()
                done_count += 1
                handle_result(done_count, len(raw_files), path, status, elapsed)

    print(f"\n완료: 성공 {success}개 / 스킵 {skipped}개 / 실패 {failed}개 → data/json/")


if __name__ == "__main__":
    main()
