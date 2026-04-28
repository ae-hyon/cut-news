"""뉴스 서비스 응답 조립 CLI.

실제 로직은 news_service.NewsService 라이브러리에 있고,
이 파일은 수동 확인용 CLI wrapper 역할만 한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from news_service import NewsService

DEFAULT_METADATA_PATH = Path("data/category_map.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="카테고리 메타데이터 기반 서비스 응답 JSON 생성")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH, help="카테고리 메타데이터 JSON 경로")
    parser.add_argument("--mode", choices=["wide", "deep", "category", "article", "categories"], required=True)
    parser.add_argument("--primary", help="대분류 이름")
    parser.add_argument("--subcategory", help="중분류 이름")
    parser.add_argument("--article-id", help="article 조회용 ID")
    parser.add_argument("--top-n", type=int, default=5)
    parser.add_argument("--include-suspicious", action="store_true")
    parser.add_argument("--min-score", type=int)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    service = NewsService(metadata_path=args.metadata)
    clean_only = not args.include_suspicious

    if args.mode == "wide":
        result = service.build_wide_view(top_n=args.top_n, clean_only=clean_only, min_score=args.min_score)
    elif args.mode == "deep":
        if not args.primary or not args.subcategory:
            raise SystemExit("deep 모드는 --primary 와 --subcategory 가 필요합니다.")
        result = service.build_deep_view(
            args.primary,
            args.subcategory,
            top_n=args.top_n,
            clean_only=clean_only,
            min_score=args.min_score,
        )
    elif args.mode == "category":
        if not args.primary:
            raise SystemExit("category 모드는 --primary 가 필요합니다.")
        result = service.get_category(
            args.primary,
            top_n=args.top_n,
            clean_only=clean_only,
            min_score=args.min_score,
        )
    elif args.mode == "article":
        if not args.article_id:
            raise SystemExit("article 모드는 --article-id 가 필요합니다.")
        result = service.get_article(args.article_id)
    else:
        result = {
            "resource": "categories",
            "categories": service.list_categories(clean_only=clean_only, min_score=args.min_score),
        }

    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
