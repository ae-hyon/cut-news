# Next session handoff

## Current branch
- `main`
- latest local commit subject before this handoff refresh: `feat: consume GitHub crawl artifacts locally` (`e1b7c7d`).
- local `main` was one commit ahead of `origin/main` before the final PR/merge cleanup; verify with `git status -sb` / `git log --oneline --decorate -5` in the next session.

## Recently landed work
- `601be69 feat: add daily feed snapshots`
  - Snapshot backend migration Phase 1~9 complete.
  - `GET /v1/me/feed` uses daily feed snapshots and marks viewed/check-in.
  - `GET /v1/me/archive?month=YYYY-MM` returns snapshot day metadata only.
  - `GET /v1/me/archive/{YYYY-MM-DD}` returns persisted snapshot items and marks viewed.
  - Article detail routes record read state; optional `snapshot_id` contributes to snapshot completion.
  - Scheduler/import success generates daily snapshots for onboarded users and writes `run_report.snapshot_generation` counters.
  - Backend docs/OpenAPI/tests were updated; last known full backend gate: `make test` -> `114 passed`.
- `8ce6849 feat: add dockerless local compose runner`
  - Added host-run `scripts/local-compose.py` for frontend/backend/crawler/scheduler without passing AI OAuth credentials into Docker containers.
  - Added Make targets: `local-up`, `local-down`, `local-ps`, `local-logs`, `local-pipeline`, `local-report`.
  - Logs/pids are stored under `.local/compose/`.
  - Default Dockerless DB is `sqlite+pysqlite:///dev-ui-test.db` unless `DATABASE_URL` is set.

## Current completed slices

Committed in local `HEAD` with subject `feat: add all-category news pipeline support`. Run `git log -1 --oneline` for the exact SHA.

### Neon/external Postgres readiness

User chose Neon instead of Supabase for a free managed external DB.

Implemented in the working tree:
- Root and backend Compose now pass through `${DATABASE_URL:-postgresql+psycopg://annoyingcap:annoyingcap@db:5432/annoyingcap}` so a root `.env` Neon URL can override the local Compose DB URL.
- `.env.example` and `apps/backend/.env.example` include commented Neon/external Postgres examples.
- `Makefile` has DB helper targets:
  - `make db-migrate` -> `cd apps/backend && PYTHONPATH=. uv run alembic upgrade head`
  - `make db-current` -> `cd apps/backend && PYTHONPATH=. uv run alembic current`
- Root `README.md` and `apps/backend/README.md` document Neon setup, migration order, and safety notes.
- `tests/test_local_compose.py` now covers Dockerless local compose env loading precedence:
  - explicit shell/Make environment wins over root `.env`
  - root `.env` wins over `apps/backend/.env`
  - backend `.env` wins over defaults
- `scripts/local-compose.py` uses the same precedence, so one-off commands like `NEWS_SOURCE=naver-all-categories NEWS_COUNT=2 make local-pipeline` are not silently overridden by root `.env`.
- `Makefile` preserves selected explicit shell environment values over included `.env` values before exporting to recipes, including `NEWS_PIPELINE_MAX_ARTICLES` for bounded pipeline smoke runs.
- Backend settings normalize plain Neon `postgresql://...` URLs to `postgresql+psycopg://...` so copied Neon URLs work with the installed psycopg driver.
- `apps/backend/tests/test_config.py` covers database URL normalization.

### News pipeline category/schedule slice

Implemented in the working tree:
- `.dev/news-pipeline-category-schedule.md` records the user-provided service taxonomy and timing notes.
- `apps/crawler/src/crawler/collect_naver.py` supports `NEWS_SOURCE=naver-all-categories` / `--source naver-all-categories`, builds queries from each category keyword plus subcategory name, dedupes original URLs, and prints/writes crawler category stats.
- Crawler output now includes `source_category` and `source_query`.
- Backend import uses `source_category` as fallback classification when category map/keywords are insufficient and counts it as `crawler_source_category`.
- Pipeline `run_report.json` includes `crawler_category_stats` when category crawl stats are printed.
- `NEWS_PIPELINE_MAX_ARTICLES=<positive-int>` is available as an optional diagnostic cap for local LLM runtime/cost control. It caps crawler raw export before summarizer, preserves crawler stats in the report, and records `max_articles`. Leave it unset for product-like real-data verification.
- Import diagnostics now distinguish `_error.json` outputs as `summary_error` / `verification_error`; a pipeline that reaches import but produces zero inserted/updated articles while drop reasons exist is marked failed at `failed_step="import"` and does not generate daily snapshots.
- GitHub Actions crawler-only schedule is defined in `.github/workflows/crawl-naver.yml`: daily 08:00 Asia/Seoul (`0 23 * * *` UTC), manual `workflow_dispatch`, requires repo secrets `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`, runs only `crawler.collect_naver`, and uploads `latest.json`, `crawl_report.json`, and `github_action_crawl_summary.json` as a 7-day artifact. It intentionally does not run summarizer/import because `codex_exec` needs a local/server Codex OAuth/session runtime.

## Runtime ports
- Backend API: `http://127.0.0.1:8000`
- Real Next frontend: `http://127.0.0.1:3000`
- Crawler API: `http://127.0.0.1:8001`
- Local Docker Postgres host port: `54329`
- `apps/test-frontend` / Vite `5173` is deprecated; do not use it as the E2E target.

## Most relevant files
- External DB/local runtime:
  - `.env.example`
  - `Makefile`
  - `README.md`
  - `docker-compose.yml`
  - `apps/backend/.env.example`
  - `apps/backend/README.md`
  - `apps/backend/docker-compose.yml`
  - `scripts/local-compose.py`
  - `tests/test_local_compose.py`
- Snapshot backend:
  - `apps/backend/app/application/services/daily_feed_snapshot_service.py`
  - `apps/backend/app/application/services/feed_service.py`
  - `apps/backend/app/presentation/api/routes/users.py`
  - `apps/backend/app/presentation/api/routes/articles.py`
  - `apps/backend/app/scripts/run_news_pipeline_job.py`
  - `apps/backend/alembic/versions/0006_daily_feed_snapshots.py`
- Category pipeline:
  - `.github/workflows/crawl-naver.yml`
  - `.dev/news-pipeline-category-schedule.md`
  - `apps/crawler/src/crawler/collect_naver.py`
  - `apps/crawler/src/crawler/schemas.py`
  - `apps/crawler/tests/test_collect_naver.py`
  - `apps/backend/app/application/services/article_ingest_service.py`
  - `apps/backend/tests/test_article_ingest_service.py`
- Local runtime/env precedence:
  - `Makefile`
  - `scripts/local-compose.py`
  - `tests/test_local_compose.py`

## Working policy
- Backend first. Do not edit `apps/frontend` unless explicitly requested.
- Backend and real Next frontend must stay contract-synced.
- Prefer backend tests/API contract checks over deprecated `apps/test-frontend` flows.
- Do not commit secrets or real `.env` values.

## Verification for current tree
- `python3 -m py_compile scripts/local-compose.py` passed.
- `python3 -m unittest tests/test_local_compose.py -q` -> 6 tests OK.
- `make test` -> 119 passed after adding bounded all-category diagnostic cap, import `_error.json` diagnostics, and zero-import guard.
- `cd apps/backend && PYTHONPATH=. uv run pytest tests/test_run_news_pipeline_job.py tests/test_article_ingest_service.py::test_load_summarized_articles_report_tracks_import_drop_reasons_and_classification_sources -q` -> 9 passed.
- `PYTHONPATH=apps/crawler/src uv run pytest apps/crawler/tests/test_collect_naver.py apps/crawler/tests/test_export_raw.py -q` -> 13 passed after adding crawl-only GitHub Actions workflow.
- `.github/workflows/crawl-naver.yml` parsed successfully with PyYAML smoke; `actionlint` is not installed locally.
- Neon DB migration succeeded: `make db-migrate` ran revisions through `0006_daily_feed_snapshots`; `make db-current` reports `0006_daily_feed_snapshots (head)`.
- `make -n db-migrate` and `make -n db-current` print the intended Alembic commands.
- `docker compose config` and `(cd apps/backend && docker compose config)` both render successfully.
- Dockerless local smoke passed for backend+crawler:
  - `make local-up SERVICES="backend crawler"`
  - `curl -sf http://127.0.0.1:8000/health`
  - `curl -sf http://127.0.0.1:8001/health`
  - `curl -sf http://127.0.0.1:8000/v1/categories` returned 10 categories.
  - `make local-down SERVICES="backend crawler"`
- Real Naver all-category crawler smoke passed with root `.env` Naver credentials:
  - command: `set -a; . ./.env; set +a; cd apps/crawler && PYTHONPATH=src uv run python -m crawler.collect_naver --source naver-all-categories --count 2 --output-dir /tmp/cut-news-naver-all-categories-smoke`
  - result: `collected 77 articles`
  - `crawler category stats`: `query_count=49`, `count_per_query=2`, `deduped_count=21`, by-category collected counts: crypto 7, economy 9, entertainment 6, global 5, lifestyle 5, politics 10, realestate 7, sports 10, stock 11, tech 7.
- Full all-category pipeline with real uncapped `NEWS_COUNT=1` was run after the diagnostic-cap policy change:
  - command: `NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline`
  - result before the zero-import guard was added: process completed in ~349s; crawler collected 45 articles from 49 queries with `max_articles=null`; import produced zero inserted/updated articles.
  - actual data diagnostics: `drop_reason_counts={"summary_error":4,"missing_summary":3}`; generated `_error.json` tails show Codex CLI `401 Unauthorized: Missing bearer or basic authentication`, so the blocker is LLM auth/runtime, not crawler query breadth.
  - follow-up fix in this tree: future runs with this shape should fail at `failed_step="import"` and skip snapshot generation instead of reporting success.

## Next best steps
1. `crawl-naver.yml` manual workflow dispatch has been verified after GitHub CLI account switching was fixed. Run `26438030302` succeeded and uploaded the expected artifact files: `latest.json`, `crawl_report.json`, and `github_action_crawl_summary.json`. Artifact summary: `source=naver-all-categories`, `count=1`, `article_count=37`, `query_count=49`, `deduped_count=12`.
2. Codex OAuth was re-logged in and verified from the real user home. Direct check passed with `HOME=/Users/reddit codex exec --skip-git-repo-check --sandbox read-only 'Reply exactly: codex-ok'`. Important pitfall: Hermes profile sessions can have `HOME=/Users/reddit/.hermes/profiles/school/home`; running the pipeline without `HOME=/Users/reddit` still sends Codex toward API-style auth and produced `401 Unauthorized: Missing bearer or basic authentication`.
3. Bounded local/server summarizer/import verification passed after setting the real HOME: `HOME=/Users/reddit NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES=3 make local-pipeline` succeeded in ~4m24s, inserted 1 article, generated 1 snapshot, and had empty `drop_reason_counts`.
4. Full uncapped local/server verification also passed after setting the real HOME and keeping the crawler service stopped to avoid macOS ephemeral-port exhaustion: `HOME=/Users/reddit DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline` succeeded in ~22m13s, collected 35 articles from 49 queries, inserted 9 articles, deleted 1 stale article, generated 1 snapshot, and reported `drop_reason_counts={"missing_summary":2}` with `max_articles=null`. This proves the product-like Naver + Codex OAuth + all-category uncapped path; it used local SQLite, not Neon.
5. Current direction: do not store crawler payloads in Neon. Use GitHub Actions artifacts as the crawler handoff (`make github-crawl-download`, then `HOME=/Users/reddit make local-pipeline-from-github`). The new pipeline mode starts at `export_raw` when `NEWS_CRAWL_INPUT_PATH` is set and loads `NEWS_CRAWL_REPORT_PATH` into `run_report.crawler_category_stats`. A bounded smoke against run `26438030302` downloaded 37 articles and verified the artifact path, but with `NEWS_PIPELINE_MAX_ARTICLES=3` it failed at import because two of the first three artifacts were short description-only items and only one JSON was produced (`drop_reason_counts={"missing_summary":1}`); this confirms orchestration, not full product data quality.
6. Remaining verification if needed: rerun the full uncapped flow against Neon (`DATABASE_URL` pooled Neon URL with `sslmode=require`) and/or rerun the GitHub artifact handoff path uncapped. Keep `HOME=/Users/reddit` on all pipeline commands so Codex uses OAuth rather than API-style auth.

## Notes
- Neon runtime should use the pooled connection string and include `sslmode=require` when Neon does not append it. Plain `postgresql://` URLs are accepted and normalized by backend settings.
- Shared/staging DB may want `SEED_ON_STARTUP=false` to avoid repeated local seed writes.
- Product category crawl mode is `NEWS_SOURCE=naver-all-categories`; `NEWS_COUNT` is per generated query.
- AI news generation 기준 시간 is `08:30:00` Asia/Seoul. Product note says `03:08:59` is pre-publication, `09:02:59(+1)` is published, and if there is no access during `09:03:00(+1)` the news archive is not generated for that user.
- `make backend-up` / `make full-up` can use external `DATABASE_URL`, but the local Postgres container may still start due to Compose dependencies. For external DB-only smoke, prefer `make local-up`.
