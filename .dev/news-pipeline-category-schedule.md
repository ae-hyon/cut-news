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

# Full pipeline with real data. NEWS_COUNT is per query; leave NEWS_PIPELINE_MAX_ARTICLES
# unset for product-like runs. Set NEWS_PIPELINE_MAX_ARTICLES only for a deliberately
# bounded diagnostic run when LLM runtime/cost must be capped.
NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 make local-pipeline
make local-report

# GitHub Actions crawl-only schedule intentionally stops before summarizer/import.
# It runs at 08:00 Asia/Seoul (23:00 UTC), uploads latest.json/crawl_report.json
# as a 7-day artifact, and requires repository secrets NAVER_CLIENT_ID / NAVER_CLIENT_SECRET.
# Summarizing/import remains local or server-side because codex_exec needs a usable
# Codex OAuth/session runtime that should not be assumed in GitHub Actions.
gh workflow run crawl-naver.yml -f source=naver-all-categories -f count=1

# Prefer artifact download over re-crawling when a successful GitHub crawl artifact exists.
# This avoids storing crawl payloads in Neon and keeps Neon as backend runtime DB only.
make github-crawl-download
HOME=/Users/reddit NEWS_PIPELINE_MAX_ARTICLES=3 make local-pipeline-from-github
make local-report-check
# Leave NEWS_PIPELINE_MAX_ARTICLES unset/empty only for a product-like full summarizer/import run.
# Product-like scheduled/server run should fail fast on any unhealthy report signal:
HOME=/Users/reddit DATABASE_URL="$DATABASE_URL" NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline-from-github
make local-report-check REPORT_CHECK_ARGS=--require-uncapped

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
- Implemented optional bounded diagnostic cap via `NEWS_PIPELINE_MAX_ARTICLES`; it appends `--max-articles` to crawler raw export, records `max_articles` in `run_report.json`, and keeps crawler category stats from the full collection. Do not set it for product-like real-data runs; use it only when intentionally capping LLM runtime/cost.
- Full all-category pipeline with real uncapped `NEWS_COUNT=1` was run after the diagnostic cap policy change:
  - first run command: `NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline`
  - result before the zero-import guard was added: process completed in ~349s (`collect` 11.7s, `summarize` 323.2s, `import` 9.7s), crawler collected 45 articles from 49 queries, `max_articles=null`, and import produced zero usable articles.
  - diagnostics from the actual generated data: `drop_reason_counts={"summary_error":4,"missing_summary":3}`. The `_error.json` tails show Codex CLI `401 Unauthorized: Missing bearer or basic authentication`, so the failure is LLM auth/runtime, not crawler query breadth.
  - Follow-up fix in this tree: `_error.json` outputs are counted as `summary_error` / `verification_error`, and a zero usable import with drop reasons now marks the pipeline failed at `failed_step="import"` and skips snapshot generation.
- Full all-category uncapped local verification later passed once Codex was forced to the real user OAuth home and the crawler service was stopped:
  - command: `HOME=/Users/reddit DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline`
  - result: success in ~22m13s (`collect` 7.9s, `summarize` 1323.1s, `import` 0.8s), `max_articles=null`, crawler collected 35 articles from 49 queries, import inserted 9 / deleted 1, and snapshot generation created 1 snapshot.
  - final diagnostics: `drop_reason_counts={"missing_summary":2}`, `classification_source_counts={"keyword_rule":9}`, `query_count=49`, `deduped_count=13`.
  - this proves the product-like Naver + Codex OAuth + all-category uncapped path with local SQLite. Neon remains a separate final DB-target smoke if required.
  - pitfall: leaving the native crawler API service running on macOS can accumulate many `127.0.0.1:8001` TIME_WAIT sockets and exhaust ephemeral ports, causing unrelated outbound Naver/Neon/GitHub requests to fail with `[Errno 49] Can't assign requested address`. Stop crawler (`make local-down SERVICES="crawler"`) and wait for sockets to drain before full pipeline or Neon checks.
- GitHub artifact handoff was verified uncapped after run `26438030302`:
  - local DB command: `HOME=/Users/reddit NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline-from-github`
  - result: success in ~12m03s, skipped crawler collection via `NEWS_CRAWL_INPUT_PATH`, summarized for ~706.5s, imported 4 articles, deleted 12 stale articles, generated 1 snapshot, and preserved crawl report stats (`query_count=49`, `collected_count=37`, `deduped_count=12`).
  - Neon command shape: explicitly pass the root `.env` Neon `DATABASE_URL` in the shell, e.g. `HOME=/Users/reddit DATABASE_URL=<root .env Neon URL> NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline-from-github`.
  - Neon result: migration at `0006_daily_feed_snapshots (head)`, success in ~16m34s, updated 3 existing articles, deleted 1 stale article, generated 1 snapshot, and Neon contained 14 articles / 1 daily snapshot / 8 snapshot items afterward.
  - operational requirement: use explicit `DATABASE_URL` for Neon-target runs because `apps/backend/.env` may point local commands at SQLite (`dev-live-smoke.db`) when commands are executed directly under `apps/backend`.
