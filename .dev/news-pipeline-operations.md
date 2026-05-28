# News pipeline operations runbook

## Goal

Run the production-like daily path without putting Naver crawl payloads in Neon:

1. GitHub Actions runs `crawl-naver.yml` at 08:00 Asia/Seoul and uploads a 7-day crawl artifact.
2. A trusted local/server runner with an OAuth-backed AI runtime downloads the latest successful artifact.
3. The runner summarizes/verifies/imports into the explicit backend `DATABASE_URL` target.
4. The runner validates `apps/summarizer/data/run_report.json` and alerts on unhealthy output.

Neon is the backend runtime DB only. GitHub artifact storage is the handoff channel for crawler payloads.

## Current production-like verification status

Status: service flow is healthy as of `main` commit `851fe59` (`fix: summarize hash-based article artifacts`).

Verified path:

1. GitHub Actions crawl artifact from `crawl-naver.yml` is downloaded.
2. The trusted local/server runner exports artifact articles into summarizer input.
3. Summarizer scores, summarizes, and verifies all artifact JSON article ids, including hash-based ids such as `a6a3cbbe2ed1`.
4. Backend import writes usable articles into the explicit DB target.
5. Daily feed snapshots are generated for onboarded users.
6. `local-report-check --require-uncapped` passes.

Latest verified run report:

- `started_at`: `2026-05-28T12:46:15+0900`
- `finished_at`: `2026-05-28T13:02:53+0900`
- `crawl_input_path`: `apps/crawler/output/github-actions/latest.json`
- `crawl_report_path`: `apps/crawler/output/github-actions/crawl_report.json`
- `max_articles`: `null` (uncapped product-like run)
- crawler stats: `query_count=49`, `count_per_query=1`, `collected_count=36`, `deduped_count=12`
- import stats: `inserted=6`, `updated=5`, `usable_imports=11`
- `drop_reason_counts`: `{}`
- snapshot generation: `attempted_user_count=3`, `generated_count=3`, `failed_count=0`
- report archive: `apps/summarizer/data/run_reports/run_2026-05-28T124615+0900.json`

Local gates after the fix:

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
# 13 passed

make test
# 123 passed

make local-report-check REPORT_CHECK_ARGS=--require-uncapped
# failures: []

python3 -m unittest tests/test_scheduled_artifact_pipeline.py -q
# OK
```

Remaining ops step: install/schedule `make ops-pipeline-from-github` on the trusted machine with stable AI runtime credentials and the Neon `DATABASE_URL` secret. The code path itself has passed the product-like artifact -> summarize -> import -> snapshot flow.

## 2026-05-28 local-runner quality check

Decision: use the user's local Mac as the trusted runner for now. OCI Always Free is not available because instance allocation failed; GitHub Actions remains crawl-only because the summarizer needs a persistent OAuth/session runtime.

Implementation direction verified in a quality DB:

- Created a disposable SQLite DB at `apps/backend/dev-quality-flow.db` and copied only user/account preference state into it.
- Left real Neon/runtime data untouched for the quality check.
- Started with empty news/feed/read/scrap tables.
- Created a dedicated Hermes profile, `cut-news-pipeline`, and verified it can answer one-shot prompts.
- Added/used `PIPELINE_LLM_BACKEND=hermes_cli` with `PIPELINE_HERMES_PROFILE=cut-news-pipeline` instead of direct `codex_exec` after Codex device-auth proved brittle.
- Ran the same operator path as the scheduled flow:

```bash
cd /Users/reddit/Project/cut-news
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$PWD/apps/backend/dev-quality-flow.db" \
SEED_ON_STARTUP=false \
AI_NEWS_GENERATION_TIME=08:30:00 \
NEWS_SCHEDULE_TIMEZONE=Asia/Seoul \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_MAX_WORKERS=3 \
NEWS_PIPELINE_MAX_ARTICLES= \
make ops-pipeline-from-github
```

Result:

- `status=success`, `failed_step=null`.
- `started_at=2026-05-28T17:09:30+0900`, `finished_at=2026-05-28T17:22:48+0900`.
- `feed_date=2026-05-28`, `max_articles=null`.
- import: `inserted=11`, `updated=0`, `usable_imports=11`.
- `drop_reason_counts={}`.
- `classification_source_counts={"keyword_rule": 11}`.
- snapshot generation: `attempted_user_count=3`, `generated_count=3`, `failed_count=0`.
- report gate: `make local-report-check REPORT_CHECK_ARGS=--require-uncapped` passed with `failures=[]`.
- backend/API smoke against the quality DB confirmed `/health` and `GET /v1/me/archive/2026-05-28` can read the generated snapshot articles.

Observed quality findings before the classifier routing fix:

- Summaries are generally usable: they preserve concrete facts and numbers, for example deal value, rate, share count, dates, and affected counts.
- Category/subcategory quality is the largest remaining product issue. Examples from the quality run:
  - 부산 BTS/K-pop tourism article was classified as `tech/tech-ai`.
  - 갤러리아 designer hat retail article was classified as `global/global-us`.
  - 무인창고 현금/허웅 재판 issue article was classified as `sports/sports-basketball`.
- The current report showed all 11 classifications came from `keyword_rule`, so the LLM/Hermes improvement did not improve category placement by itself.
- Product-date behavior needs a policy pass. The scheduler pipeline generated `feed_date=2026-05-28`, while `GET /v1/me/feed` currently serves the previous KST date by route policy. The generated 2026-05-28 snapshot was visible through daily archive, but home feed lookup can appear empty if pipeline and API date policies diverge.
- Runtime cost/latency: Hermes CLI full run with 11 artifact articles took about 13 minutes with `PIPELINE_MAX_WORKERS=3`. Effort/model settings should be explicit before scheduling daily runs.

Recommended near-term operator settings while quality work continues:

```bash
PIPELINE_LLM_BACKEND=hermes_cli
PIPELINE_HERMES_PROFILE=cut-news-pipeline
PIPELINE_MAX_WORKERS=3
# keep NEWS_PIPELINE_MAX_ARTICLES empty for product-like runs
```

Do not treat `effort` tuning as the first fix for category quality. Effort can improve summary/verification deliberation, but the observed misclassification was mostly caused by keyword-rule classification and weak taxonomy routing. The first code fix now prefers crawler `source_query`/`source_category` metadata before broad keyword rules; compare effort/model variants only on a fixed article fixture set after this routing layer is in place.

Follow-up implementation status after the plan started:

- `GET /v1/me/feed` now uses today's KST product feed date, matching the 08:30 scheduler's `feed_date` bucket.
- Classification fixtures were added for crawler source-query precedence over broad keyword rules.
- Import classification now reports `crawler_source_query` when source query maps cleanly to a supported subcategory.
- `scripts/check-pipeline-report.py` now keeps product-like runs passing but emits `quality_warnings=["all_classifications_from_keyword_rule"]` when every usable import came from broad keyword rules.
- Hermes CLI supports optional `PIPELINE_HERMES_MODEL` and `PIPELINE_HERMES_PROVIDER`. `hermes chat --help` does not expose a reasoning-effort flag, so low/medium/high effort comparison is currently a legacy Codex-axis experiment (`PIPELINE_CODEX_REASONING_EFFORT`) or a model/provider comparison for Hermes.

### 2026-05-28 hash-id summarizer fix

Root cause of the previous partial import/missing summary symptom:

- GitHub crawler artifact article ids are hash-like strings, for example `a6a3cbbe2ed1`.
- The summarizer pipeline steps 3/4/5 previously selected only `[0-9]*.json` files.
- Hash ids beginning with letters were silently skipped by score/summarize/verify and later appeared as `missing_summary` at import time.

Fix:

- `apps/summarizer/pipeline/step3_score.py`, `step4_summarize.py`, and `step5_verify.py` now process all `*.json` article files while excluding `*_error.json` outputs.
- `apps/summarizer/pipeline/common.py` now retries transient `codex_exec` failures/timeouts via `PIPELINE_CODEX_MAX_ATTEMPTS` while failing fast on non-retryable auth/config errors such as `401 Unauthorized` or missing Codex configuration.
- Regression tests cover hash article ids through step3/4/5 and Codex retry/non-retry behavior.

## Preconditions

- Repo checkout: `/Users/reddit/Project/cut-news`.
- GitHub CLI can read `ae-hyon/cut-news` workflow artifacts.
- One OAuth-backed summarizer runtime works from the local runner:
  - Preferred current path: `hermes --profile cut-news-pipeline chat -Q -q 'Reply exactly: ok' --toolsets ''`.
  - Legacy/direct Codex path, if used: `HOME=/Users/reddit codex exec --skip-git-repo-check --sandbox read-only 'Reply exactly: codex-ok'`.
- Backend target DB is explicit. For Neon, use the pooled URL and `sslmode=require`.
- Do not set `NEWS_PIPELINE_MAX_ARTICLES` for scheduled/product-like runs.
- Recommended shared/staging DB env: `SEED_ON_STARTUP=false` for API service startup.

## One-shot product-like run

Prefer passing `DATABASE_URL` from the scheduler secret store instead of relying on nested `.env` resolution.

```bash
cd /Users/reddit/Project/cut-news
HOME=/Users/reddit \
DATABASE_URL='<Neon pooled DATABASE_URL with sslmode=require>' \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
make ops-pipeline-from-github
```

Alternative for a local operator shell where root `.env` already contains the correct Neon URL:

```bash
cd /Users/reddit/Project/cut-news
make ops-pipeline-from-github OPS_PIPELINE_ARGS='--load-dotenv'
```

`make ops-pipeline-from-github` wraps `scripts/run-scheduled-artifact-pipeline.py` and runs:

1. `make local-pipeline-from-github`
2. `make local-report-check` with `REPORT_CHECK_ARGS=--require-uncapped`

It prints a JSON summary with a redacted database target label. It exits non-zero when either command fails.

## Dry run

Use dry run before installing a scheduler:

```bash
cd /Users/reddit/Project/cut-news
HOME=/Users/reddit \
DATABASE_URL='<Neon pooled DATABASE_URL with sslmode=require>' \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
make ops-pipeline-from-github OPS_PIPELINE_ARGS='--dry-run'
```

## Alert hooks

The wrapper can notify on failure through either or both of these env vars:

- `PIPELINE_ALERT_COMMAND`: shell command that receives the JSON failure summary on stdin.
- `PIPELINE_ALERT_WEBHOOK_URL`: generic JSON webhook; body shape is `{ "text": "<pretty JSON summary>" }`.

Example local alert command that appends to a private log:

```bash
PIPELINE_ALERT_COMMAND='tee -a /tmp/cut-news-pipeline-alerts.jsonl >/dev/null'
```

Do not commit real webhook URLs or secrets.

## Cron example

Schedule after the 08:00 Asia/Seoul GitHub crawl artifact has had time to complete. 08:40 KST is the current conservative default.

```cron
# KST host example. Keep DATABASE_URL/alert secrets outside the repository.
40 8 * * * cd /Users/reddit/Project/cut-news && HOME=/Users/reddit DATABASE_URL='<Neon URL>' PIPELINE_LLM_BACKEND=hermes_cli PIPELINE_HERMES_PROFILE=cut-news-pipeline make ops-pipeline-from-github >> /Users/reddit/Project/cut-news/.local/compose/logs/ops-pipeline.log 2>&1
```

For UTC hosts, 08:40 KST is 23:40 UTC on the previous day:

```cron
40 23 * * * cd /Users/reddit/Project/cut-news && HOME=/Users/reddit DATABASE_URL='<Neon URL>' PIPELINE_LLM_BACKEND=hermes_cli PIPELINE_HERMES_PROFILE=cut-news-pipeline make ops-pipeline-from-github >> /Users/reddit/Project/cut-news/.local/compose/logs/ops-pipeline.log 2>&1
```

## Failure policy

`make local-report-check REPORT_CHECK_ARGS=--require-uncapped` fails on:

- `run_report.status != success`
- `failed_step` present
- zero usable imports (`inserted + updated == 0`)
- `snapshot_generation.failed_count > 0`
- `max_articles` set during a product-like scheduled run

Drop reasons such as `missing_summary` are included in the summary for observability. They are not fatal when at least one usable article was inserted/updated and the pipeline status is success.

## Operator triage order

1. Read the JSON summary printed by `make ops-pipeline-from-github`.
2. Inspect `apps/summarizer/data/run_report.json` and the archived report path inside it.
3. If `failed_step=summarize` or errors mention AI auth, first re-check `hermes --profile cut-news-pipeline chat -Q -q 'Reply exactly: ok' --toolsets ''`; if using legacy Codex, re-check `HOME=/Users/reddit codex exec ...`.
4. If artifact download failed, inspect `gh run list --workflow crawl-naver.yml --status success --limit 3`.
5. If Neon connection failed, run `make db-current` with the exact scheduled `DATABASE_URL`.
6. If imports are zero with drop reasons, inspect generated `_error.json` files under `apps/summarizer/data/summarized` / `verified`.
7. Re-run only after confirming whether the same feed date already has viewed snapshots; viewed snapshots are intentionally preserved.

## Current recommended next step

Install the scheduler on the trusted machine that has stable Codex OAuth and the Neon secret. Keep the repo target as the runbook and script above; keep actual crontab/systemd/Hermes job secrets outside git.
