"""
각 스텝 결과를 읽어 품질 평가 리포트 생성
reports/evaluation_{step}.json + reports/summary.md
"""

import json
from pathlib import Path
from pipeline.common import JSON_DIR, SCORED_DIR, SUMMARIZED_DIR, VERIFIED_DIR

REPORTS_DIR = Path(__file__).parent / "reports"
HEADLINE_TARGETS = {
    "headline_34": 34,
    "headline_58": 58,
    "headline_89": 89,
}


def _build_proximity_metrics(values_by_field: dict[str, list[int]]) -> dict[str, dict[str, int]]:
    metrics = {}
    for field, target in HEADLINE_TARGETS.items():
        values = values_by_field.get(field, [])
        metrics[field] = {
            "target": target,
            "exact_target": sum(1 for value in values if value == target),
            "within_2": sum(1 for value in values if abs(value - target) <= 2),
            "within_4": sum(1 for value in values if abs(value - target) <= 4),
        }
    return metrics


def evaluate_step2():
    """Step 2 (raw→JSON) 품질 평가"""
    files = sorted(JSON_DIR.glob("[0-9]*.json"))
    results = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        has_title = bool(d.get("title"))
        has_content = bool(d.get("content")) and len(d.get("content", "")) >= 50
        has_date = bool(d.get("date"))
        results.append({
            "id": f.stem,
            "title": d.get("title", "")[:40],
            "has_title": has_title,
            "has_content": has_content,
            "has_date": has_date,
            "content_len": len(d.get("content", "")),
            "ok": has_title and has_content,
        })

    ok = sum(1 for r in results if r["ok"])
    return {
        "total": len(results),
        "ok": ok,
        "ok_rate": f"{ok/len(results)*100:.1f}%" if results else "0%",
        "avg_content_len": int(sum(r["content_len"] for r in results) / len(results)) if results else 0,
        "items": results,
    }


def evaluate_step3():
    """Step 3 (점수 할당) 품질 평가"""
    files = sorted(SCORED_DIR.glob("[0-9]*.json"))
    results = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        score = d.get("score")
        results.append({
            "id": f.stem,
            "title": d.get("_title", "")[:40],
            "score": score,
            "reason": d.get("reason", ""),
            "valid": isinstance(score, (int, float)) and 0 <= score <= 100,
        })

    valid = [r for r in results if r["valid"]]
    scores = [r["score"] for r in valid]
    return {
        "total": len(results),
        "valid": len(valid),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "min_score": min(scores) if scores else 0,
        "max_score": max(scores) if scores else 0,
        "distribution": {
            "0~30": sum(1 for s in scores if s <= 30),
            "31~60": sum(1 for s in scores if 31 <= s <= 60),
            "61~80": sum(1 for s in scores if 61 <= s <= 80),
            "81~100": sum(1 for s in scores if s > 80),
        },
        "items": sorted(results, key=lambda r: r.get("score") or 0, reverse=True),
    }


def evaluate_step4():
    """Step 4 (요약) 품질 평가"""
    files = sorted(SUMMARIZED_DIR.glob("[0-9]*.json"))
    results = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        violations = d.get("_violations", [])
        h34 = d.get("_headline_34_len", 0)
        h58 = d.get("_headline_58_len", 0)
        h89 = d.get("_headline_89_len", 0)
        summary_len = len(d.get("summary", ""))
        results.append({
            "id": f.stem,
            "title": d.get("_title", "")[:40],
            "headline_34": d.get("headline_34", ""),
            "headline_58": d.get("headline_58", ""),
            "headline_89": d.get("headline_89", ""),
            "summary": d.get("summary", "")[:80],
            "h34_len": h34,
            "h58_len": h58,
            "h89_len": h89,
            "summary_len": summary_len,
            "violations": violations,
            "ok": len(violations) == 0,
        })

    ok = sum(1 for r in results if r["ok"])
    avg = lambda vals: round(sum(vals) / len(vals), 1) if vals else 0
    proximity = _build_proximity_metrics({
        "headline_34": [r["h34_len"] for r in results],
        "headline_58": [r["h58_len"] for r in results],
        "headline_89": [r["h89_len"] for r in results],
    })
    return {
        "total": len(results),
        "ok": ok,
        "violation_rate": f"{(len(results)-ok)/len(results)*100:.1f}%" if results else "0%",
        "avg_h34_len": avg([r["h34_len"] for r in results]),
        "avg_h58_len": avg([r["h58_len"] for r in results]),
        "avg_h89_len": avg([r["h89_len"] for r in results]),
        "avg_summary_len": avg([r["summary_len"] for r in results]),
        "headline_proximity": proximity,
        "items": results,
    }


def evaluate_step5():
    """Step 5 (할루시네이션 검증) 품질 평가"""
    files = sorted(VERIFIED_DIR.glob("[0-9]*.json"))
    results = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8"))
        verdict = d.get("verdict", "unknown")
        items = d.get("hallucinations", [])
        results.append({
            "id": f.stem,
            "title": d.get("_title", "")[:40],
            "verdict": verdict,
            "hallucinations": items,
            "confidence": d.get("confidence", 0),
        })

    clean = sum(1 for r in results if r["verdict"] == "clean")
    suspicious = sum(1 for r in results if r["verdict"] == "suspicious")
    return {
        "total": len(results),
        "clean": clean,
        "suspicious": suspicious,
        "clean_rate": f"{clean/len(results)*100:.1f}%" if results else "0%",
        "suspicious_items": [r for r in results if r["verdict"] == "suspicious"],
        "items": results,
    }


def write_markdown_report(step2, step3, step4, step5) -> str:
    proximity = step4.get("headline_proximity", {})
    proximity_lines = []
    for field in ("headline_34", "headline_58", "headline_89"):
        metric = proximity.get(field)
        if not metric:
            continue
        short = field.replace("headline_", "h")
        proximity_lines.append(
            f"  - {short} target={metric['target']} exact={metric['exact_target']} ±2={metric['within_2']} ±4={metric['within_4']}"
        )
    lines = [
        "# 파이프라인 품질 평가 리포트\n",
        "## Step 2: raw → JSON 변환",
        f"- 총 {step2['total']}개 / 정상 {step2['ok']}개 ({step2['ok_rate']})",
        f"- 평균 본문 길이: {step2['avg_content_len']}자\n",
        "## Step 3: 중요도 점수",
        f"- 유효 점수: {step3['valid']}/{step3['total']}개",
        f"- 평균 점수: {step3['avg_score']} (min {step3['min_score']} / max {step3['max_score']})",
        f"- 분포: {step3['distribution']}\n",
        "## Step 4: 요약 생성",
        f"- 총 {step4['total']}개 / 글자수 통과 {step4['ok']}개",
        f"- 위반율: {step4['violation_rate']}",
        f"- 평균 headline 길이: h34={step4['avg_h34_len']}자 / h58={step4['avg_h58_len']}자 / h89={step4['avg_h89_len']}자",
        f"- 평균 summary 길이: {step4['avg_summary_len']}자",
    ]
    if proximity_lines:
        lines.append("- headline 목표 근접도:")
        lines.extend(proximity_lines)
    lines.extend([
        "",
        "## Step 5: 할루시네이션 검증",
        f"- 🟢 clean: {step5['clean']}개 ({step5['clean_rate']})",
        f"- 🔴 suspicious: {step5['suspicious']}개",
    ])
    if step5["suspicious_items"]:
        lines.append("\n### 의심 기사:")
        for item in step5["suspicious_items"]:
            lines.append(f"  - [{item['id']}] {item['title']}")
            for h in item["hallucinations"]:
                lines.append(f"    → {h}")
    return "\n".join(lines)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print("품질 평가 리포트 생성 중...\n")

    step2 = evaluate_step2()
    step3 = evaluate_step3()
    step4 = evaluate_step4()
    step5 = evaluate_step5()

    for name, data in [("step2_json", step2), ("step3_score", step3),
                       ("step4_summary", step4), ("step5_verify", step5)]:
        path = REPORTS_DIR / f"{name}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  ✅ {path}")

    md = write_markdown_report(step2, step3, step4, step5)
    md_path = REPORTS_DIR / "summary.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  ✅ {md_path}")

    print("\n" + md)


if __name__ == "__main__":
    main()
