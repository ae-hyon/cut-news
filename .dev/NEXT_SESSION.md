# Next session handoff

## Current branch
- `main`
- Latest verified local commit: current `HEAD`; latest pushed baseline was `0ab84de`, with a new classifier/stale-artifact cleanup slice in progress.
- Local branch may be ahead of `origin/main`; check `git status --short --branch` before continuing.

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

### Candidate-first summarization and selective best-of slice

Current working-tree slice after the Hermes/profile quality work:

- Step 3 scoring now preserves crawler metadata in scored artifacts: `_source_category`, `_source_query`, and `_content_source`.
- Step 4 can reduce full summarization volume with `PIPELINE_SELECTED_PER_CATEGORY=<N>` by selecting category-balanced top-N articles from Step 3 scores before calling the LLM summarizer. Empty/unset keeps the previous all-article behavior.
- Step 4 can selectively apply best-of summaries with `PIPELINE_BEST_OF_N=<N>` and `PIPELINE_BEST_OF_SCORE_THRESHOLD=<score>`; default is single-summary. When enabled, only scored high-importance articles at/above the threshold generate multiple candidates, and lower-score articles remain single-call. The current empirically selected threshold is `80` because `85` did not trigger on the latest artifact set.
- Best-of selection records audit metadata in summarized artifacts: `_best_of_n`, `_best_of_candidate_index`, `_best_of_quality_score`, `_best_of_candidates`, and candidate errors if any.
- Operator/Make env propagation includes `PIPELINE_SELECTED_PER_CATEGORY`, `PIPELINE_BEST_OF_N`, and `PIPELINE_BEST_OF_SCORE_THRESHOLD`. Root `.env` is locally configured with the Hermes/profile/candidate-first defaults; it is gitignored and should not be committed.
- Step 4 writes `apps/summarizer/data/summary_selection.json`; backend import reads it so intentionally unselected low-score JSON files are not counted as `missing_summary`.
- Backend import now maps reproductive-health terms such as `심부전`, `폐경`, and `호르몬` to `lifestyle/lifestyle-health`, fixing the 2026-05-29 disposable run's single `category_unmapped` drop.
- Docs updated: `.dev/news-pipeline-operations.md`, `.dev/news-pipeline-quality-improvement-plan.md`, and `BE_AI_ARCHITECTURE_NOTES.md`.

Verified for this slice:

```text
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q  # 23 passed
cd apps/backend && PYTHONPATH=. uv run pytest tests/test_article_ingest_service.py -q  # 22 passed
python3 -m unittest tests/test_scheduled_artifact_pipeline.py -q  # OK
make test  # 131 passed
git diff --check  # pass
```

Latest disposable quality evidence:

- First run with threshold `85`: success but best-of did not trigger; import showed `missing_summary=1` because unselected JSON was still considered by import.
- Follow-up code added `summary_selection.json` and backend import filtering for selected article ids.
- Second run with `.env` threshold `80`: `status=success`, `feed_date=2026-05-29`, `selected_count=9/10`, Step 4 summarized 9 and verified 9, best-of applied to 3 articles, report gate `failures=[]`, snapshots `attempted=3/generated=3/failed=0`.
- Re-loading the same artifacts after the health-category mapping fix yields 9 importable rows and `drop_reason_counts={}`.

Suggested disposable quality run after tests pass:

```bash
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$PWD/apps/backend/dev-quality-flow.db" \
SEED_ON_STARTUP=false \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_MAX_WORKERS=3 \
PIPELINE_SELECTED_PER_CATEGORY=3 \
PIPELINE_BEST_OF_N=3 \
PIPELINE_BEST_OF_SCORE_THRESHOLD=80 \
NEWS_PIPELINE_MAX_ARTICLES= \
make ops-pipeline-from-github
```

### Production-like scheduled artifact pipeline

Landed locally through current `HEAD` (`fix: align feed date and source-query classification`); `851fe59 fix: summarize hash-based article artifacts` is the source fix commit for hash-id summarizer processing.

Current status: the full service flow is verified healthy for the code path that matters in production-like operation:
GitHub scheduled crawl artifact -> local/server OAuth-backed summarizer -> backend import into explicit DB -> daily feed snapshot generation -> report gate.

Latest verified run report (`apps/summarizer/data/run_report.json`):
- `status=success`, `failed_step=null`, `max_articles=null`.
- GitHub artifact input: `apps/crawler/output/github-actions/latest.json` plus `crawl_report.json`.
- Crawler stats from the artifact: `query_count=49`, `count_per_query=1`, `collected_count=36`, `deduped_count=12`.
- Import stats: `inserted=6`, `updated=5`, `usable_imports=11`.
- `drop_reason_counts={}`.
- Snapshot generation: `attempted_user_count=3`, `generated_count=3`, `failed_count=0`.
- Archive report: `apps/summarizer/data/run_reports/run_2026-05-28T124615+0900.json`.

Fix included in `851fe59`:
- Summarizer step3/4/5 file selection now handles hash-based artifact article ids (`*.json` excluding `*_error.json`) instead of only numeric filenames.
- `codex_exec` now retries transient CLI failures/timeouts and fails fast for non-retryable auth/config errors.
- Regression tests cover hash-id processing and retry behavior.

Validation after landing:
- `PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q` -> 13 passed.
- `make test` -> 123 passed.
- `make local-report-check REPORT_CHECK_ARGS=--require-uncapped` -> `failures: []`.
- `python3 -m unittest tests/test_scheduled_artifact_pipeline.py -q` -> OK.

Remaining operational work is not a code-flow blocker: install the scheduler on the trusted machine with stable OAuth-backed AI runtime credentials and an explicit Neon `DATABASE_URL`, then run `make ops-pipeline-from-github` on the desired cadence.

### Hermes-profile local runner quality slice

Current working-tree slice:
- Added Hermes CLI summarizer backend support (`PIPELINE_LLM_BACKEND=hermes_cli`) with profile selection via `PIPELINE_HERMES_PROFILE`.
- Created/verified dedicated profile `cut-news-pipeline` outside the repo.
- Verified `make ops-pipeline-from-github` on a disposable SQLite quality DB with user preferences copied but news/feed/read/scrap data empty.
- Quality-run result: `status=success`, `import inserted=11`, `usable_imports=11`, `drop_reason_counts={}`, snapshots `attempted=3/generated=3/failed=0`, report check `failures=[]`.
- Tests after the code change: `PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q` -> 16 passed; `cd apps/backend && PYTHONPATH=. uv run pytest tests/ -q` -> 126 passed.

Implemented in the working tree after the initial quality run:
- `/v1/me/feed` uses today's KST product feed date to match the scheduler-generated `feed_date`; snapshot generation now selects articles from the previous publication date for that product bucket (for example `feed_date=2026-05-29` uses `published_at=2026-05-28`).
- Source-query classification fixtures cover broad keyword false positives and live-audit cases where crawler source queries were wrong (`global/중국` for ETRI AI, `realestate/청약` for a consumer fraud article, noisy stock/global links inside tax-policy content).
- Import quality gate now also drops summary/article topic mismatches (`quality_gate:topic_mismatch`) when a generated headline/summary has no salient overlap with the original source title; this targets mixed-content cases such as the observed `허웅 재판` article being summarized as unrelated `무인창고 68억 은닉` content.
- Import classification now trusts crawler `source_query`/`source_category` only when title/summary contain supporting evidence, and broad keyword rules use title + generated summary instead of raw crawler body to avoid related-link/page chrome noise.
- `apps/summarizer/run_pipeline.py` clears stale downstream artifacts at run start so old JSON/scored/summarized/verified files cannot be imported into the next completed run.
- `make local-report-check` emits non-failing `quality_warnings` for all-keyword-rule classification runs.
- Hermes backend supports optional `PIPELINE_HERMES_MODEL` and `PIPELINE_HERMES_PROVIDER`; reasoning effort remains a legacy Codex-only axis until Hermes CLI exposes a supported flag.

Remaining gap:
- Codex legacy low/medium/high effort comparison is blocked by local Codex OAuth (`refresh_token_reused`/401). Re-run after `HOME=/Users/reddit codex login --device-auth` succeeds, or keep daily operation on Hermes model/provider variants.

Fixed-variant eval:
- `.dev/news-pipeline-fixed-variant-eval.json` compares Hermes default profile vs explicit `PIPELINE_HERMES_PROVIDER=openai-codex`, `PIPELINE_HERMES_MODEL=gpt-5.5` on 3 stable articles. Both variants returned parseable summaries with no headline length violations.

New planning doc:
- `.dev/news-pipeline-quality-improvement-plan.md` describes the next implementation order: land Hermes runner support, fix feed-date visibility, add classification fixtures, improve classifier routing, add quality warnings, then evaluate effort/model settings on a fixed article set.

### Earlier local runtime and category-pipeline slices

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
- Backend API: `http://127.0.0.1:8030`
- Real Next frontend: `http://127.0.0.1:3030`
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
  - `curl -sf http://127.0.0.1:8030/health`
  - `curl -sf http://127.0.0.1:8001/health`
  - `curl -sf http://127.0.0.1:8030/v1/categories` returned 10 categories.
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

Current priority after the candidate-first/best-of slice:
1. Commit the verified working tree once the diff remains scoped to Step 3/4 summarizer selection/best-of behavior, operator env propagation, backend import filtering/classification, tests, and docs.
2. If the user approves touching Neon, re-run the artifact import path against Neon with the `.env` defaults and confirm `drop_reason_counts={}` in the scheduled run report.
3. Record the final scheduled env in the actual scheduler/cron secret store and keep DB/alert secrets outside git.
4. Install the local Mac scheduler only after the operator env is final and secrets stay outside git.
5. Codex low/medium/high effort comparison remains blocked until `HOME=/Users/reddit codex login --device-auth` succeeds; otherwise continue Hermes profile/model-provider evaluation.

Historical verified steps:
1. `crawl-naver.yml` manual workflow dispatch has been verified after GitHub CLI account switching was fixed. Run `26438030302` succeeded and uploaded the expected artifact files: `latest.json`, `crawl_report.json`, and `github_action_crawl_summary.json`. Artifact summary: `source=naver-all-categories`, `count=1`, `article_count=37`, `query_count=49`, `deduped_count=12`.
2. Codex OAuth was re-logged in and verified from the real user home. Direct check passed with `HOME=/Users/reddit codex exec --skip-git-repo-check --sandbox read-only 'Reply exactly: codex-ok'`. Important pitfall: Hermes profile sessions can have `HOME=/Users/reddit/.hermes/profiles/school/home`; running the pipeline without `HOME=/Users/reddit` still sends Codex toward API-style auth and produced `401 Unauthorized: Missing bearer or basic authentication`.
3. Bounded local/server summarizer/import verification passed after setting the real HOME: `HOME=/Users/reddit NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES=3 make local-pipeline` succeeded in ~4m24s, inserted 1 article, generated 1 snapshot, and had empty `drop_reason_counts`.
4. Full uncapped local/server verification also passed after setting the real HOME and keeping the crawler service stopped to avoid macOS ephemeral-port exhaustion: `HOME=/Users/reddit DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline` succeeded in ~22m13s, collected 35 articles from 49 queries, inserted 9 articles, deleted 1 stale article, generated 1 snapshot, and reported `drop_reason_counts={"missing_summary":2}` with `max_articles=null`. This proves the product-like Naver + Codex OAuth + all-category uncapped path; it used local SQLite, not Neon.
5. GitHub Actions artifact handoff was verified uncapped with local runtime: `HOME=/Users/reddit NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline-from-github` downloaded run `26438030302`, used `apps/crawler/output/github-actions/latest.json`, skipped crawler collection, summarized for ~11m46s, imported 4 articles, deleted 12 stale articles, generated 1 snapshot, and preserved `crawler_category_stats` (`query_count=49`, `collected_count=37`, `deduped_count=12`).
6. The same GitHub artifact handoff was verified against Neon by explicitly exporting the root `.env` `DATABASE_URL`: Neon migration was at `0006_daily_feed_snapshots (head)`, `HOME=/Users/reddit DATABASE_URL=<root .env Neon URL> NEWS_PIPELINE_MAX_ARTICLES= make local-pipeline-from-github` succeeded, updated 3 existing articles, deleted 1 stale article, generated 1 snapshot, and left Neon with 14 articles / 1 daily snapshot / 8 snapshot items. Backend health and `/v1/categories` passed when started with the same explicit Neon URL.
7. Neon target smoke passed with the root `.env` `DATABASE_URL` explicitly exported: URL points to Neon pooler host `ep-twilight-dream-aokoffyt-pooler.c-2.ap-southeast-1.aws.neon.tech`, `sslmode=require`, backend settings normalize it to `postgresql+psycopg`, Alembic reports `0006_daily_feed_snapshots (head)`, and the DB currently has 14 articles / 1 daily snapshot / 8 snapshot items / 10 categories. `make local-up SERVICES="backend"` with the same explicit Neon URL served `/health` and `/v1/categories` successfully.
8. Added operational report validation for the post-crawl summarizer/import runner: `make local-report-check` wraps `scripts/check-pipeline-report.py` and fails on non-success status, `failed_step`, zero inserted+updated imports, `snapshot_generation.failed_count > 0`, and `--require-uncapped` product-like runs that accidentally set `NEWS_PIPELINE_MAX_ARTICLES`.
9. Remaining product work is deployment wiring: schedule the post-crawl summarizer/import runner after the 08:00 GitHub crawl artifact exists, ensure it always runs with `HOME=/Users/reddit` and explicit `DATABASE_URL`, and route non-zero `make local-report-check REPORT_CHECK_ARGS=--require-uncapped` output to the operator alert channel.

## Notes
- Neon runtime should use the pooled connection string and include `sslmode=require` when Neon does not append it. Plain `postgresql://` URLs are accepted and normalized by backend settings.
- Shared/staging DB may want `SEED_ON_STARTUP=false` to avoid repeated local seed writes.
- Product category crawl mode is `NEWS_SOURCE=naver-all-categories`; `NEWS_COUNT` is per generated query.
- AI news generation 기준 시간 is `08:30:00` Asia/Seoul. Product note says `03:08:59` is pre-publication, `09:02:59(+1)` is published, and if there is no access during `09:03:00(+1)` the news archive is not generated for that user.
- `make ops-pipeline-from-github` wraps the scheduled product-like flow: download latest GitHub crawl artifact, run summarizer/import with explicit `HOME`/`DATABASE_URL`, validate the run report with `--require-uncapped`, and optionally alert via `PIPELINE_ALERT_COMMAND` or `PIPELINE_ALERT_WEBHOOK_URL`. Full runbook: `.dev/news-pipeline-operations.md`.
