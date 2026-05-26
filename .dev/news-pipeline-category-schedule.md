# News pipeline category and schedule policy

## Crawler category taxonomy

The real Naver collection mode should use the same service category IDs that the backend exposes to users. Use `NEWS_SOURCE=naver-all-categories` to crawl all categories; `NEWS_COUNT` means count per query, not total count, in this mode.

```json
[
  {
    "id": "stock",
    "name": "주식시장",
    "keywords": ["코스피", "나스닥", "S&P500"],
    "subcategories": [
      { "id": "stock-domestic", "name": "국내주식" },
      { "id": "stock-overseas", "name": "해외주식" },
      { "id": "stock-etf", "name": "ETF" },
      { "id": "stock-unlisted", "name": "비상장주식" }
    ]
  },
  {
    "id": "crypto",
    "name": "가상자산",
    "keywords": ["비트코인", "이더리움", "알트코인"],
    "subcategories": [
      { "id": "crypto-bitcoin", "name": "비트코인" },
      { "id": "crypto-altcoin", "name": "알트코인" },
      { "id": "crypto-defi", "name": "DeFi" },
      { "id": "crypto-nft", "name": "NFT" }
    ]
  },
  {
    "id": "realestate",
    "name": "부동산",
    "keywords": ["아파트", "청약", "전세"],
    "subcategories": [
      { "id": "realestate-apt", "name": "아파트" },
      { "id": "realestate-subscription", "name": "청약" },
      { "id": "realestate-lease", "name": "전세/월세" },
      { "id": "realestate-commercial", "name": "상업용" }
    ]
  },
  {
    "id": "politics",
    "name": "정치",
    "keywords": ["국회", "대통령", "정당"],
    "subcategories": [
      { "id": "politics-domestic", "name": "국내정치" },
      { "id": "politics-diplomacy", "name": "외교" },
      { "id": "politics-policy", "name": "정책" }
    ]
  },
  {
    "id": "economy",
    "name": "경제",
    "keywords": ["금리", "환율", "GDP"],
    "subcategories": [
      { "id": "economy-macro", "name": "거시경제" },
      { "id": "economy-finance", "name": "금융" },
      { "id": "economy-trade", "name": "무역" }
    ]
  },
  {
    "id": "tech",
    "name": "IT/테크",
    "keywords": ["AI", "반도체", "스타트업"],
    "subcategories": [
      { "id": "tech-ai", "name": "AI" },
      { "id": "tech-semiconductor", "name": "반도체" },
      { "id": "tech-startup", "name": "스타트업" },
      { "id": "tech-bigtech", "name": "빅테크" }
    ]
  },
  {
    "id": "entertainment",
    "name": "연예",
    "keywords": ["K-POP", "드라마", "영화"],
    "subcategories": [
      { "id": "entertainment-kpop", "name": "K-POP" },
      { "id": "entertainment-drama", "name": "드라마" },
      { "id": "entertainment-movie", "name": "영화" }
    ]
  },
  {
    "id": "sports",
    "name": "스포츠",
    "keywords": ["축구", "야구", "NBA"],
    "subcategories": [
      { "id": "sports-soccer", "name": "축구" },
      { "id": "sports-baseball", "name": "야구" },
      { "id": "sports-basketball", "name": "농구" },
      { "id": "sports-esports", "name": "e스포츠" }
    ]
  },
  {
    "id": "global",
    "name": "국제",
    "keywords": ["미국", "중국", "EU"],
    "subcategories": [
      { "id": "global-us", "name": "미국" },
      { "id": "global-china", "name": "중국" },
      { "id": "global-europe", "name": "유럽" },
      { "id": "global-asia", "name": "아시아" }
    ]
  },
  {
    "id": "lifestyle",
    "name": "라이프",
    "keywords": ["건강", "여행", "맛집"],
    "subcategories": [
      { "id": "lifestyle-health", "name": "건강" },
      { "id": "lifestyle-travel", "name": "여행" },
      { "id": "lifestyle-food", "name": "맛집" }
    ]
  }
]
```

Implementation notes:
- `apps/crawler/src/crawler/collect_naver.py` owns this crawl taxonomy as `CRAWL_CATEGORIES`.
- `build_category_queries()` crawls each category keyword and each subcategory display name.
- `collect_all_category_articles()` dedupes repeated original URLs across category queries and writes `source_category` / `source_query` into crawler output.
- Backend import can use `source_category` as a fallback classification source when summarizer/category-map metadata is absent.
- Pipeline run reports include `crawler_category_stats` when the crawler prints category stats.

## Schedule / archive behavior reference

- AI news generation 기준 시간: every morning at `08:30:00` Asia/Seoul (`AI_NEWS_GENERATION_TIME=08:30:00`).
- News publication/access reference from the product note:
  - `03:08:59` is before publication.
  - `09:02:59(+1)` is considered published for the next-day window.
  - If the user has not accessed during `09:03:00(+1)`, the news archive is not generated for that user.
- Current backend snapshot model generates/imports the daily feed snapshot after successful pipeline import for onboarded users; archive/check-in behavior must preserve the above product timing when future frontend/scheduler logic is adjusted.

## Operator commands

```bash
# Real Naver all-category collection; requires NAVER_CLIENT_ID / NAVER_CLIENT_SECRET.
# Prefer this crawler-only smoke first; NEWS_COUNT is per generated query.
set -a; . ./.env; set +a
cd apps/crawler
PYTHONPATH=src uv run python -m crawler.collect_naver --source naver-all-categories --count 2 --output-dir /tmp/cut-news-naver-all-categories-smoke

# Full pipeline. Use cautiously: count=2 produced 77 articles in the 2026-05-26 smoke
# and exceeded a 600s summarizer timeout. Add/use a bounded smoke mode before relying
# on this as a quick gate.
NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 make local-pipeline
make local-report

# Single-query Naver collection remains available.
NEWS_SOURCE=naver-search NEWS_QUERY=경제 NEWS_COUNT=20 make local-pipeline

# Seeded/dev-safe collection remains available when Naver credentials are absent.
NEWS_SOURCE=seeded make local-pipeline
```

## 2026-05-26 live smoke notes

- Crawler-only all-category smoke passed with real root `.env` Naver credentials.
- Command: `set -a; . ./.env; set +a; cd apps/crawler && PYTHONPATH=src uv run python -m crawler.collect_naver --source naver-all-categories --count 2 --output-dir /tmp/cut-news-naver-all-categories-smoke`
- Result: `collected 77 articles`.
- Stats: `query_count=49`, `count_per_query=2`, `deduped_count=21`; collected by category: crypto 7, economy 9, entertainment 6, global 5, lifestyle 5, politics 10, realestate 7, sports 10, stock 11, tech 7.
- Full `NEWS_SOURCE=naver-all-categories NEWS_COUNT=2 make local-pipeline` reached all-category crawler mode after env precedence fixes, but exceeded a 600s timeout during summarizer processing because the all-category crawl produced ~77-78 raw articles. Generated summarizer artifacts were restored/cleaned from the working tree.
