#!/usr/bin/env python3.11
"""뉴스 요약 CLI 테스트 도구.

실제 요약 로직은 news_service.NewsSummarizer 라이브러리에 있고,
이 파일은 로컬 수동 검증용 thin wrapper 역할만 한다.
"""

from __future__ import annotations

import argparse
import sys
import time

from news_service import NewsSummarizer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="뉴스 기사 요약 테스트")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="연합뉴스 기사 URL")
    src.add_argument("--file", help="기사 JSON 파일 경로 (예: data/json/009.json)")

    parser.add_argument("--backend", choices=["codex_exec", "hermit_http"], default="codex_exec")
    parser.add_argument("--model", default="gpt-5.4-mini")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--verify", action="store_true", help="사실 검증도 함께 실행")
    return parser.parse_args()


def print_result(article: dict, result: dict, elapsed: float) -> None:
    print("\n" + "─" * 72)
    print(f"원문 제목: {article.get('title', '')}")
    print(f"날짜: {article.get('date', '')} | 기자: {article.get('author', '')}")
    print(f"본문 길이: {len(article.get('content', ''))}자")
    print("─" * 72)
    print(f"headline_34 ({len(result.get('headline_34', ''))}자): {result.get('headline_34', '')}")
    print(f"headline_58 ({len(result.get('headline_58', ''))}자): {result.get('headline_58', '')}")
    print(f"headline_89 ({len(result.get('headline_89', ''))}자): {result.get('headline_89', '')}")
    print(f"\nsummary:\n{result.get('summary', '')}")
    print(f"\n소요 시간: {elapsed:.1f}초")

    violations = result.get("_violations", [])
    if violations:
        print("길이 위반:")
        for item in violations:
            print(f"- {item}")
    else:
        print("길이 검증: 통과")

    verify_result = result.get("_verify")
    if verify_result:
        print(f"사실 검증 verdict: {verify_result.get('verdict', 'unknown')}")
        for item in verify_result.get("hallucinations", []):
            print(f"- {item}")


def main() -> int:
    args = parse_args()
    summarizer = NewsSummarizer(
        backend=args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )

    try:
        article = summarizer.fetch_article(args.url) if args.url else summarizer.load_article_file(args.file)
    except Exception as e:
        print(f"기사 로드 실패: {e}", file=sys.stderr)
        return 1

    print(f"backend={args.backend} model={args.model} reasoning_effort={args.reasoning_effort}")
    if args.url:
        print(f"url={args.url}")
    else:
        print(f"file={args.file}")

    t0 = time.time()
    try:
        result = summarizer.summarize(article, verify=args.verify)
    except Exception as e:
        print(f"요약 실패: {e}", file=sys.stderr)
        return 1
    elapsed = time.time() - t0

    print_result(article, result, elapsed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
