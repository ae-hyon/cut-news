# Next session handoff

## Current branch
- `main`
- latest local commit subject: `feat: add all-category news pipeline support` (run `git log -1 --oneline` for the exact SHA)
- based on `8ce6849 feat: add dockerless local compose runner`; push state should be verified with `git status -sb` / `git log --oneline --decorate -3` in the next session.

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
- `Makefile` preserves selected explicit shell environment values over included `.env` values before exporting to recipes.
- Backend settings normalize plain Neon `postgresql://...` URLs to `postgresql+psycopg://...` so copied Neon URLs work with the installed psycopg driver.
- `apps/backend/tests/test_config.py` covers database URL normalization.

### News pipeline category/schedule slice

Implemented in the working tree:
- `.dev/news-pipeline-category-schedule.md` records the user-provided service taxonomy and timing notes.
- `apps/crawler/src/crawler/collect_naver.py` supports `NEWS_SOURCE=naver-all-categories` / `--source naver-all-categories`, builds queries from each category keyword plus subcategory name, dedupes original URLs, and prints/writes crawler category stats.
- Crawler output now includes `source_category` and `source_query`.
- Backend import uses `source_category` as fallback classification when category map/keywords are insufficient and counts it as `crawler_source_category`.
- Pipeline `run_report.json` includes `crawler_category_stats` when category crawl stats are printed.

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
- `make test` -> 118 passed after the Neon/external DB and news category/schedule slices.
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
- Full all-category pipeline smoke was attempted with `NEWS_SOURCE=naver-all-categories NEWS_COUNT=2 make local-pipeline` after env precedence fixes; it correctly reached all-category crawler mode but timed out at 600s during summarizer processing because the all-category crawl produced ~77-78 raw articles. Generated summarizer data was restored/cleaned from the working tree afterward.

## Next best steps
1. Decide and implement a bounded all-category full-pipeline smoke mode before rerunning summarizer/import end-to-end. Current `NEWS_COUNT=2` all-category crawl yields ~77 articles and exceeded a 600s smoke timeout in the summarizer stage. Safer options:
   - add a pipeline-level max article cap for smoke runs after crawl/export,
   - run summarizer on a sampled subset while retaining crawler category stats,
   - or use `NEWS_COUNT=1` only after estimating runtime/LLM cost.
2. Re-run full all-category pipeline only after the bounded smoke path exists:
   ```bash
   NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 make local-pipeline
   make local-report
   ```
3. Push `main` if this local commit should be shared remotely, after checking `git status -sb` and remote policy.

## Notes
- Neon runtime should use the pooled connection string and include `sslmode=require` when Neon does not append it. Plain `postgresql://` URLs are accepted and normalized by backend settings.
- Shared/staging DB may want `SEED_ON_STARTUP=false` to avoid repeated local seed writes.
- Product category crawl mode is `NEWS_SOURCE=naver-all-categories`; `NEWS_COUNT` is per generated query.
- AI news generation 기준 시간 is `08:30:00` Asia/Seoul. Product note says `03:08:59` is pre-publication, `09:02:59(+1)` is published, and if there is no access during `09:03:00(+1)` the news archive is not generated for that user.
- `make backend-up` / `make full-up` can use external `DATABASE_URL`, but the local Postgres container may still start due to Compose dependencies. For external DB-only smoke, prefer `make local-up`.
