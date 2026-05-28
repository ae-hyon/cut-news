# News Pipeline Quality Improvement Implementation Plan

> **For Hermes:** Use `cut-news-backend` plus `test-driven-development`/`subagent-driven-development` if implementing this plan task-by-task.

**Goal:** Make the local 08:30-style news pipeline produce visible, correctly dated, correctly classified daily feed items with measurable summary quality.

**Architecture:** Keep GitHub Actions crawl-only and run summarization/import/snapshot on the local Mac through a dedicated Hermes profile. Separate three concerns: (1) runner stability, (2) product-date/feed visibility, and (3) category/summary quality. Do not rely on higher LLM effort alone; first add deterministic observability and fixtures, then evaluate model/effort changes on the same fixed data.

**Tech Stack:** FastAPI backend, SQLAlchemy, pytest, Naver crawler artifact handoff, summarizer pipeline, Hermes CLI profile `cut-news-pipeline`, local/Neon DB selected by explicit `DATABASE_URL`.

---

## Current verified state

- Runner direction: local Mac runner is the practical path for now.
- AI backend direction: prefer `PIPELINE_LLM_BACKEND=hermes_cli` with `PIPELINE_HERMES_PROFILE=cut-news-pipeline`.
- Quality-check run used a disposable SQLite DB (`apps/backend/dev-quality-flow.db`) and did not mutate real Neon runtime data.
- Operator path verified: `make ops-pipeline-from-github`.
- Latest quality-check result:
  - `status=success`, `failed_step=null`.
  - `feed_date=2026-05-28`.
  - `max_articles=null`.
  - import `inserted=11`, `updated=0`, `usable_imports=11`.
  - `drop_reason_counts={}`.
  - snapshots `attempted_user_count=3`, `generated_count=3`, `failed_count=0`.
  - `make local-report-check REPORT_CHECK_ARGS=--require-uncapped` passed.
- Summary quality: generally usable; facts and numeric details are preserved.
- Biggest issues:
  1. Category/subcategory misclassification.
  2. Pipeline `feed_date` vs `GET /v1/me/feed` product-date mismatch.
  3. Model/effort/runtime settings are not yet codified as an evaluated policy.

## Non-goals for the next slice

- Do not edit frontend unless the user explicitly asks.
- Do not mutate real Neon news/feed rows for experiments; use a disposable DB first.
- Do not commit `.env`, tokens, webhook URLs, or database connection strings.
- Do not assume effort tuning fixes classification until there is a fixture-based comparison.

---

## Phase 0: Land the Hermes runner backend support safely

### Task 0.1: Keep current source changes scoped

**Objective:** Make sure the uncommitted Hermes CLI backend support is the only source change in the runner slice.

**Files:**
- Modify: `apps/summarizer/pipeline/common.py`
- Modify: `apps/summarizer/news_schema.py`
- Modify: `Makefile`
- Modify: `scripts/run-scheduled-artifact-pipeline.py`
- Test: `apps/summarizer/tests/test_common_retry.py`

**Steps:**
1. Review `git diff` and confirm it only adds `hermes_cli` support and env propagation.
2. Confirm `apps/summarizer/data/*` generated fixtures are restored/unchanged before staging.
3. Run:
   ```bash
   PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
   make test
   ```
4. Expected:
   - summarizer tests pass.
   - backend tests pass.
5. Commit after review:
   ```bash
   git add Makefile apps/summarizer/pipeline/common.py apps/summarizer/news_schema.py apps/summarizer/tests/test_common_retry.py scripts/run-scheduled-artifact-pipeline.py
   git commit -m "feat: support Hermes CLI news summarizer backend"
   ```

### Task 0.2: Add runner smoke documentation to the runbook

**Objective:** Ensure future scheduling uses Hermes profile by default and does not re-open Codex device auth unless intentionally using legacy Codex.

**Files:**
- Modify: `.dev/news-pipeline-operations.md`
- Modify: `.dev/NEXT_SESSION.md`

**Verification:**
```bash
git diff --check
```
Expected: no whitespace errors.

---

## Phase 1: Fix the product-date/feed visibility mismatch

### Task 1.1: Decide the date policy in code comments/tests

**Status:** implemented. `/v1/me/feed` now uses today's KST product feed date so it matches the scheduled 08:30 pipeline `feed_date` bucket.

**Objective:** Choose one explicit product policy and make it testable.

**Recommended policy:** For the 08:30 KST morning digest, pipeline-generated `feed_date` and `GET /v1/me/feed` should refer to the same product bucket. The most direct behavior is: `feed_date = today in Asia/Seoul` for the morning digest generated at 08:30, and home feed reads today's persisted snapshot.

**Files:**
- Modify: `apps/backend/app/presentation/api/routes/users.py`
- Modify or add tests under `apps/backend/tests/`
- Consult: `apps/backend/app/scripts/run_news_pipeline_job.py`

**Step 1: Add failing test**
Add/extend route/service tests that prove `/v1/me/feed` asks for the same product date that the scheduler writes. If the current test harness cannot freeze time at route level, extract the date function first in a tiny utility.

**Expected current failure:** Existing `_current_feed_date()` subtracts one day, so a same-day scheduler snapshot is not returned.

**Step 2: Implement central date helper**
Create or reuse a single helper for current product feed date. Keep `NEWS_SCHEDULE_TIMEZONE`/`Asia/Seoul` behavior explicit.

**Step 3: Verify**
Run:
```bash
cd apps/backend && PYTHONPATH=. uv run pytest tests/test_*feed* tests/test_*snapshot* -q
make test
```
Expected: focused and full backend tests pass.

### Task 1.2: Add a live smoke script or documented command for exact archive/feed dates

**Objective:** Prevent future confusion where daily archive shows data but home feed appears empty.

**Files:**
- Modify: `.dev/news-pipeline-operations.md`
- Optional create: `scripts/smoke-quality-feed.py` if repeated manual smoke becomes painful.

**Acceptance criteria:** A future operator can run one command against a disposable DB and see:
- latest `run_report.feed_date`
- `/v1/me/feed` date/count
- `/v1/me/archive/{feed_date}` count
- whether they match

---

## Phase 2: Make category quality observable and fixture-based

### Task 2.1: Capture a small misclassification fixture set

**Status:** implemented for broad-keyword false positives via `apps/backend/tests/fixtures/article_classification_cases.json` and `apps/backend/tests/test_article_ingest_classification_quality.py`.

**Objective:** Turn observed bad classifications into repeatable tests/evaluation cases.

**Files:**
- Create: `apps/backend/tests/fixtures/article_classification_cases.json`
- Test: `apps/backend/tests/test_article_ingest_classification_quality.py`

**Fixture candidates from the 2026-05-28 quality run:**
- 부산 BTS/K-pop tourism article: should not become `tech/tech-ai`; likely `entertainment/entertainment-kpop` or `lifestyle/lifestyle-travel` depending product taxonomy decision.
- 갤러리아 designer hat retail article: should not become `global/global-us`; likely `lifestyle` or a new commerce/retail bucket if taxonomy expands.
- 무인창고 현금/허웅 재판 issue article: should not become `sports/sports-basketball`; likely exclude from finance-focused feed, or classify under politics/domestic/legal if kept.

**Step 1: Write failing tests**
Tests should call the existing derivation path in `article_ingest_service.py`, not duplicate classification logic.

**Step 2: Run failing tests**
```bash
cd apps/backend && PYTHONPATH=. uv run pytest tests/test_article_ingest_classification_quality.py -q
```
Expected: at least the current misclassified cases fail.

### Task 2.2: Use crawler metadata only when the article text supports it

**Status:** tightened after live DB audit. `_derive_categories` now uses stronger exact source subcategory, then crawler metadata only when title/summary contain supporting evidence for the source query/category, and only then broad keyword rules. Keyword matching now uses title + generated summary rather than raw crawler body, because raw pages can include related-link noise such as unrelated `청약`, `주가`, `미국`, or `농구` text.

**Objective:** Reduce false positives where generic words like `AI`, `미국`, `농구`, `청약`, or `주가` inside unrelated crawler page content push the article to the wrong category.

**Files:**
- Modify: `apps/backend/app/application/services/article_ingest_service.py`
- Test: `apps/backend/tests/test_article_ingest_service.py`

**Implementation direction:**
1. If the summarizer JSON contains `source_category` plus `source_query`, use `CRAWLER_SOURCE_QUERY_SUBCATEGORY_ALIASES` only when title/summary support the query.
2. Fall back to `crawler_source_category` only when title/summary support the broad source category.
3. Use broad `KEYWORD_RULES` only after stronger source metadata and exact source subcategory checks fail.
4. Keep observability via `classification_source`: `crawler_source_query`, `crawler_source_category`, `source_subcategory`, `keyword_rule`.

**Verification:**
```bash
cd apps/backend && PYTHONPATH=. uv run pytest tests/test_article_ingest_service.py -q
make test
```

### Task 2.3: Add a report gate for suspicious classification source mix

**Status:** implemented as a non-failing warning. `make local-report-check` now includes `quality_warnings`, and current historical run reports with all `keyword_rule` imports emit `all_classifications_from_keyword_rule` while keeping `failures=[]`.

**Objective:** Surface runs where all articles are classified by weak keyword rules.

**Files:**
- Modify: `scripts/check-pipeline-report.py`
- Test: existing or new test for report checks.

**Behavior:** Do not fail product runs immediately. Start with warning/summary output:
- `classification_source_counts.keyword_rule == usable_imports` should be reported as a quality warning.
- Later, after stronger classifier is deployed, consider making this a soft threshold.

---

## Phase 3: Evaluate effort/model changes without guessing

### Task 3.1: Add explicit Hermes effort/model env names

**Status:** partially implemented for supported Hermes CLI flags. `PIPELINE_HERMES_MODEL` and `PIPELINE_HERMES_PROVIDER` are available. `hermes chat --help` does not expose a reasoning-effort flag, so do not add `PIPELINE_HERMES_REASONING_EFFORT` unless the CLI gains a supported option.

**Objective:** Make effort tunable for Hermes CLI as well as legacy Codex.

**Files:**
- Modify: `apps/summarizer/pipeline/common.py`
- Modify: `scripts/run-scheduled-artifact-pipeline.py`
- Test: `apps/summarizer/tests/test_common_retry.py` or new test file.

**Proposed envs:**
```bash
PIPELINE_HERMES_PROFILE=cut-news-pipeline
PIPELINE_HERMES_MODEL=<optional model override; passed as hermes chat --model>
PIPELINE_HERMES_PROVIDER=<optional provider override; passed as hermes chat --provider>
PIPELINE_CODEX_REASONING_EFFORT=low|medium|high  # legacy codex_exec only
```

**Caution:** Only add flags that the installed Hermes CLI actually supports. Verify with:
```bash
hermes chat --help
```
Do not invent unsupported flags.

### Task 3.2: Build a fixed-article evaluation command

**Status:** implemented as `scripts/evaluate-fixed-summary-variants.py`; latest output is `.dev/news-pipeline-fixed-variant-eval.json`.

**Current result:** Hermes default profile and explicit `PIPELINE_HERMES_PROVIDER=openai-codex` / `PIPELINE_HERMES_MODEL=gpt-5.5` both passed 3 fixed articles with no headline length violations. Legacy Codex `PIPELINE_CODEX_REASONING_EFFORT=low` failed before evaluation because local Codex OAuth returned `refresh_token_reused`/401; low/medium/high effort remains blocked until re-login.

**Objective:** Compare supported Hermes model/provider settings and legacy Codex low/medium/high effort on the exact same article set.

**Files:**
- Created: `scripts/evaluate-fixed-summary-variants.py`
- Output: `.dev/news-pipeline-fixed-variant-eval.json`

**Method:**
1. Select a fixed artifact or fixture set of 10-15 articles.
2. Run summarizer with each candidate setting into isolated output dirs or archived reports.
3. Measure:
   - summary contract pass/fail
   - hallucination verifier result
   - average latency
   - character length compliance
   - manual classification quality labels
   - cost/throughput if available
4. Choose the lowest effort that passes quality.

**Initial hypothesis:**
- Summary quality may improve slightly with higher effort.
- Category quality will not meaningfully improve until classification is changed, because current import classification source is `keyword_rule`, not LLM category reasoning.

### Task 3.3: Record an effort policy

**Objective:** Codify the chosen daily setting.

**Files:**
- Modify: `.dev/news-pipeline-operations.md`
- Modify: `.dev/NEXT_SESSION.md`

**Acceptance criteria:** The runbook states:
- default backend (`hermes_cli`)
- profile (`cut-news-pipeline`)
- worker count
- effort/model setting
- when to raise effort temporarily
- how to compare a candidate model/effort before changing daily ops

---

## Phase 4: Re-run end-to-end quality gate on disposable DB, then real target

### Task 4.1: Disposable DB final run

**Status:** passed after classifier routing fix. Disposable DB run produced `status=success`, `usable_imports=9`, `classification_source_counts={"crawler_source_query": 9}`, `quality_warnings=[]`, snapshots `attempted=3/generated=3/failed=0`; API smoke confirmed same-day `/v1/me/feed` and `/v1/me/archive/2026-05-28` visibility.

**Objective:** Prove date visibility, classification quality, and summary quality without touching Neon.

**Command shape:**
```bash
cd /Users/reddit/Project/cut-news
QUALITY_DB="$PWD/apps/backend/dev-quality-flow.db"
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$QUALITY_DB" \
SEED_ON_STARTUP=false \
AI_NEWS_GENERATION_TIME=08:30:00 \
NEWS_SCHEDULE_TIMEZONE=Asia/Seoul \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_MAX_WORKERS=3 \
NEWS_PIPELINE_MAX_ARTICLES= \
make ops-pipeline-from-github
```

**Verify:**
- `run_report.status=success`.
- `drop_reason_counts={}` or explain any drops.
- `/v1/me/feed` and `/v1/me/archive/{run_report.feed_date}` agree on visible item counts.
- Misclassification fixture examples no longer regress.

### Task 4.2: Real DB trial only after user approval

**Status:** approved in the follow-up request and executed against Neon. The real DB run produced `status=success`, `import_updated=11`, `usable_imports=11`, `drop_reason_counts={}`, `classification_source_counts={"crawler_source_query": 11}`, `quality_warnings=[]`, snapshots `attempted=3/generated=3/failed=0`.

**Objective:** Run against Neon only after the disposable DB gates pass and the user confirms.

**Required before running:**
- Explicit `DATABASE_URL` exported from secret store/root `.env`.
- Confirm user wants real news/feed rows reset or updated.
- Confirm no generated artifacts are staged.

---

## Next best implementation order

1. Commit current `hermes_cli` backend support after tests/diff review.
2. Fix product-date/feed visibility mismatch.
3. Add classification quality fixtures and improve classifier source priority.
4. Add classification quality warnings to report check.
5. Evaluate effort/model settings on a fixed fixture set.
6. Record final scheduler settings and then install the local Mac scheduler.

## Suggested first commands next session

```bash
cd /Users/reddit/Project/cut-news
git status --short --branch
git diff --stat
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest apps/summarizer/tests -q
make test
```
