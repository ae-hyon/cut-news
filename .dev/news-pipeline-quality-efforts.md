# News pipeline quality improvement efforts

Last updated: 2026-05-30 09:05 KST

Purpose: record the engineering and evaluation work behind the news pipeline quality improvements so the material can be reused in later 발표 자료. This document focuses on what was attempted, why it mattered, what changed in the product pipeline, and what evidence exists.

## One-line summary for presentation

We moved the daily news pipeline from a brittle crawl -> summarize -> keyword-import flow to an observable, fixture-tested, OAuth-backed pipeline with category-aware selection, verifier gates, LLM editorial taxonomy judgment, and repeatable model/effort evaluation.

## Problem observed

The production-like path was technically running, but quality was not yet presentation-safe.

1. Feed visibility mismatch
   - The scheduled pipeline wrote one product `feed_date`, while `/v1/me/feed` could read a different date bucket.
   - Result: archive data existed but the home feed could appear empty.

2. Weak category quality
   - Early imports classified all usable rows through broad `keyword_rule` fallback.
   - Generic page/body noise such as `AI`, `미국`, `농구`, `청약`, or `주가` could push articles into the wrong service category.
   - Concrete examples from the quality audit:
     - 부산 BTS/K-pop tourism article -> incorrectly routed to `tech/tech-ai`.
     - 갤러리아 designer hat retail article -> incorrectly routed to `global/global-us`.
     - 허웅 재판 / 무인창고 mixed-content case -> incorrectly routed to `sports/sports-basketball` or rejected only late.
     - Samsung Electronics compensation/shareholder-return article -> company-name heuristics could over-route to `tech`, while the article topic was better treated as `economy`.

3. Summary quality edge cases
   - Short market bulletins sometimes used meta narration such as “기사 제목과 본문은 ... 전했습니다” instead of reader-facing news content.
   - Reporter/author metadata could leak into headlines or summaries when the source article was short.

4. Runtime and model policy were implicit
   - Direct Codex CLI OAuth was brittle (`refresh_token_reused`/401 observed locally).
   - There was no fixed-article matrix to justify the daily model/effort setting.
   - Full all-category summarization could become expensive and slow without a controlled selection policy.

## Quality improvement work performed

### 1. Made the operator path reproducible and OAuth-backed

Changed/verified:
- Preferred daily summarizer backend is now Hermes CLI:
  - `PIPELINE_LLM_BACKEND=hermes_cli`
  - `PIPELINE_HERMES_PROFILE=cut-news-pipeline`
  - `PIPELINE_HERMES_PROVIDER=openai-codex`
  - `PIPELINE_HERMES_MODEL=gpt-5.5`
  - `PIPELINE_HERMES_REASONING_EFFORT=medium`
- `make ops-pipeline-from-github` is the documented operator path.
- GitHub Actions remains crawl-only; local/server runner handles OAuth-backed summarization/import.
- `NEWS_PIPELINE_MAX_ARTICLES` is treated as diagnostic-only and must stay empty for product-like verification.

Why this matters:
- Keeps credentials and OAuth session on a trusted machine.
- Allows the daily path to be repeated with the same command and report gates.
- Avoids silently evaluating a different runtime from the one used by scheduled operation.

### 2. Fixed product feed date visibility

Changed/verified:
- `/v1/me/feed` now reads the same KST product feed date bucket that the 08:30 scheduler writes.
- Snapshot generation maps that product bucket to the previous article publication date where needed.

Why this matters:
- Prevents the “pipeline succeeded but home feed looks empty” failure mode.
- Makes archive and feed smoke checks explainable in demos.

### 3. Added fixture-based classification quality tests

Changed/verified:
- Added repeatable classification fixtures for broad-keyword false positives.
- Backend tests exercise the real import classification path instead of duplicating logic in tests.
- Report checks emit quality warnings when all classifications come from weak keyword rules.

Why this matters:
- Misclassification examples are now regression tests, not just manual notes.
- Future category changes can be judged against known bad cases.

### 4. Reworked import category routing from brittle fallback to layered evidence

Current routing priority:
1. High-confidence Step 3 LLM editorial category, when it matches the supported taxonomy.
2. Strong source subcategory/category-map metadata.
3. Crawler `source_query` / `source_category`, only when title or generated summary supports that category.
4. Broad keyword rules as last fallback.

Important implementation detail:
- Keyword rules use title + generated summary, not raw crawler body, because raw pages can contain unrelated related-link or page-chrome text.

Why this matters:
- Avoids hard-coding one-off fixes such as “Samsung Electronics always equals tech”.
- Lets the model judge the actual article topic, while deterministic fallbacks remain available when LLM category metadata is absent or low-confidence.

### 5. Added LLM editorial taxonomy judgment in Step 3

Changed/verified:
- Step 3 now asks the LLM to emit:
  - `editorial_primary_category`
  - `editorial_subcategory`
  - `editorial_category_confidence`
  - `editorial_category_reason`
- Supported taxonomy is explicitly listed in the prompt.
- Backend import accepts valid high-confidence editorial categories before crawler/keyword fallbacks.

Observed evidence:
- The Samsung Electronics compensation/shareholder-return article was judged as:
  - primary: `economy`
  - subcategory: `economy-finance`
  - confidence: 86
  - reason: compensation, shareholder return, interest-rate and corporate-finance topic.

Why this matters:
- Category quality can improve based on article meaning, not source query or company-name heuristics.
- The decision is auditable because confidence and reason are persisted in the scored artifact.

### 6. Added candidate-first summarization and selective best-of

Changed/verified:
- Step 3 preserves crawler metadata so Step 4 can perform category-balanced selection.
- `PIPELINE_SELECTED_PER_CATEGORY=3` limits full summarization to selected top articles per source category.
- `PIPELINE_BEST_OF_N=3` generates multiple candidates only for high-score articles.
- `PIPELINE_BEST_OF_SCORE_THRESHOLD=80` is the current empirically selected threshold.
- Step 4 writes `summary_selection.json`; backend import reads it so intentionally unselected articles are not counted as missing summaries.

Why this matters:
- Controls LLM cost/runtime while preserving category coverage.
- Spends extra quality effort only on high-importance articles.
- Makes selected vs. unselected articles explicit in artifacts.

### 7. Tightened summary prompt and verifier-oriented retry guidance

Changed/verified:
- Step 4 system prompt bans reporter-name padding and `기자` phrasing unless the reporter is the article subject.
- Step 4 prompt bans source-meta narration such as “기사 제목/본문/원문이 전했다” in short bulletins.
- Retry guidance reinforces the same rule when verifier feedback detects metadata leakage.

Why this matters:
- Improves reader-facing quality for short articles where the LLM is tempted to pad with metadata.
- Reduces `quality_gate:verdict_not_clean` drops from otherwise usable articles.

### 8. Added stale-artifact and import-health protections

Changed/verified:
- Pipeline clears stale downstream artifacts at run start.
- Import diagnostics distinguish summary/verification error JSON outputs.
- Zero usable import with drop reasons is treated as an unhealthy run.
- `make local-report-check` can require uncapped product-like runs and surfaces quality warnings.

Why this matters:
- Prevents old JSON/scored/summarized files from contaminating a later run.
- Turns silent quality failures into reportable operational signals.

## Evidence collected so far

### Baseline quality-run findings before the classifier fixes

Disposable SQLite quality DB run:
- `status=success`
- `usable_imports=11`
- `drop_reason_counts={}`
- `classification_source_counts={"keyword_rule": 11}`
- snapshots generated for 3 preference users

Interpretation:
- Runtime path worked, but category quality relied entirely on weak keyword fallback.

### After crawler-source classification routing fix

Disposable and Neon runs showed:
- `classification_source_counts={"crawler_source_query": 9}` or `{"crawler_source_query": 11}`
- `drop_reason_counts={}` on clean follow-up runs
- snapshot generation completed for onboarded users
- report check returned `failures=[]`

Interpretation:
- Category routing moved from broad keyword fallback to stronger source-query evidence.

### Candidate-first / selective best-of evidence

2026-05-29 disposable/Neon evidence:
- selected 9 of 10 available articles
- best-of applied to 3-4 high-score articles depending on run
- 9 clean summaries after reporter-metadata prompt fix
- `usable_imports=9`
- `drop_reason_counts={}`
- snapshots generated for 3 users on Neon
- report check returned `failures=[]`

Interpretation:
- The candidate-first policy reduced summarization volume while preserving a clean import path.

### Fixed-variant model/effort evaluation

File: `.dev/news-pipeline-fixed-variant-eval.json`

Current winner:
- `openai-codex / gpt-5.5 / medium`
- 10 repeats across 2 fixed articles
- success rate: 1.0
- headline length violations: 0
- summary length penalty count: 0
- sampled verifier results: clean

Rejected/blocked alternatives:
- `gpt-5.4-mini-low` was faster in a quick matrix but accumulated headline length violations in repeated checks.
- Legacy direct Codex low/medium/high comparison is blocked until local Codex OAuth is repaired.

Interpretation:
- The daily model/effort policy is not just guessed; it is backed by repeatable fixed-article evidence.

### 2026-05-30 disposable rerun evidence before latest editorial-category code path

Latest archived run before this documentation pass:
- report: `apps/summarizer/data/run_reports/run_2026-05-30T054545+0900.json`
- `status=success`
- `failed_step=null`
- `feed_date=2026-05-30`
- `max_articles=null`
- import: `inserted=9`, `updated=0`, `skipped=0`
- `drop_reason_counts={}`
- `quality_gate_skip_counts={}`
- `classification_source_counts={"crawler_source_category": 6, "keyword_rule": 3}`
- snapshots: `attempted_user_count=0` because that disposable DB had no copied user preferences

Interpretation:
- The report gate is clean, but classification source mix still has room to improve through the new Step 3 editorial category path.

## Presentation-friendly before/after framing

Before:
- Pipeline completion was visible, but quality was hard to explain.
- Category came from broad keyword fallback.
- Date policy could hide successful snapshots from the home feed.
- Model/effort selection was not measured.
- Short summaries could include meta narration or reporter metadata.

After:
- Operator path is reproducible with `make ops-pipeline-from-github`.
- Feed date and archive date behavior is policy-driven and test-covered.
- Category has a layered decision model: LLM editorial judgment -> source evidence -> keyword fallback.
- Known misclassification cases are fixtures.
- Summary generation has selection, best-of, verifier gates, and artifact audit metadata.
- Model/effort defaults are backed by a fixed-article evaluation report.
- Report checks distinguish runtime failure from quality warnings.

## 2026-05-30 documentation-pass quality test rerun

Commands rerun after documenting this quality slice:

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest \
  apps/summarizer/tests/test_step3_editorial_category.py \
  apps/summarizer/tests/test_step4_contract.py \
  apps/summarizer/tests/test_pipeline_file_selection.py \
  apps/summarizer/tests/test_common_retry.py -q
# 22 passed

cd apps/backend && PYTHONPATH=. uv run pytest \
  tests/test_article_ingest_service.py \
  tests/test_article_ingest_classification_quality.py \
  tests/test_run_news_pipeline_job.py -q
# 36 passed

python3 -m unittest tests/test_scheduled_artifact_pipeline.py tests/test_local_compose.py -q
# Ran 13 tests: OK

.venv/bin/python -m pytest tests/test_evaluate_fixed_summary_variants.py -q
# 4 passed

make local-report-check REPORT_CHECK_ARGS=--require-uncapped
# failures=[]; quality_warnings=[]; usable_imports=9; drop_reason_counts={}

git diff --check
# passed
```

Interpretation:
- The new editorial-category contract, summary prompt contract, import classification fixtures, scheduled wrapper behavior, fixed-variant evaluation helper, and report gate all pass after the documentation update.
- This was a regression/quality-gate rerun against existing artifacts, not a new expensive LLM product-like pipeline execution.

## 2026-05-30 fresh LLM product-like disposable run

Command rerun against a disposable SQLite DB with the real GitHub crawl artifact and Hermes LLM path:

```bash
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$PWD/apps/backend/dev-quality-flow.db" \
SEED_ON_STARTUP=false \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_HERMES_PROVIDER=openai-codex \
PIPELINE_HERMES_MODEL=gpt-5.5 \
PIPELINE_HERMES_REASONING_EFFORT=medium \
PIPELINE_MAX_WORKERS=3 \
PIPELINE_SELECTED_PER_CATEGORY=3 \
PIPELINE_BEST_OF_N=3 \
PIPELINE_BEST_OF_SCORE_THRESHOLD=80 \
NEWS_PIPELINE_MAX_ARTICLES= \
make ops-pipeline-from-github
```

Fresh run report:
- report: `apps/summarizer/data/run_reports/run_2026-05-30T092850+0900.json`
- `status=success`, `failed_step=null`
- runtime: `09:28:50+0900` -> `09:52:20+0900`; summarize step `1406.475s`
- `feed_date=2026-05-30`, `max_articles=null`
- first import pass: `inserted=8`, `updated=0`, `deleted=8`, `skipped=0`
- `classification_source_counts={"editorial_category": 8}`
- `quality_warnings=[]`, report gate `failures=[]`
- snapshots: `attempted_user_count=3`, `generated_count=3`, `failed_count=0`

Key quality finding from this fresh run:
- The new Step 3 editorial category path worked in the real LLM path: all importable articles were classified by `editorial_category`; no article needed crawler or keyword fallback.
- Two otherwise clean summaries were dropped by `quality_gate:topic_mismatch`. Manual review showed these were false positives in the heuristic, not bad summaries:
  - 부산 피란수도 세계유산 등재 article: title said `부산의 도전`, summary/headline said `부산 피란수도 유산 ... 세계유산 등재 도전`.
  - 보은 김용식배 축구대회 article: title said `보은서 ... 축구대회`, summary/headline said `보은 ... 축구장서 ... 축구대회`.
- Root cause: the topic-mismatch guard used exact Korean eojeol token overlap and treated first title-token overlap after headline position 4 as suspicious. That was too strict for Korean particles/compounds such as `부산의` vs `부산`, `보은서` vs `보은`, and `축구대회` vs `축구장서`.

Follow-up fix from the run:
- Added Korean topic token normalization for common particles/suffixes.
- Added compatible token matching for Korean compounds/substrings.
- Kept the original safety behavior for real mixed-topic padding where title terms only appear late after unrelated headline content.
- Added regression tests:
  - allow 부산/세계유산 and 보은/축구대회 legitimate overlaps
  - still reject the prior `무인창고 현금 68억` + `허웅 명예훼손 재판` mixed-topic case

Post-fix re-import evaluation on the same fresh LLM artifacts:
- `row_count=10`
- `quality_gate_skip_counts={}`
- `drop_reason_counts={}`
- `classification_source_counts={"editorial_category": 10}`
- actual import into the disposable DB: `inserted=2`, `updated=8`, `deleted=0`, `skipped=0`

Manual quality review of the 10 generated summaries:
- verifier verdict: 10/10 `clean`
- verifier confidence range: 96-100
- `_violations=[]` for all 10
- categories all came from editorial taxonomy:
  - politics/diplomacy: 백악관·이란 협상 레드라인
  - lifestyle/health: SNS 비교·직장인 박탈감
  - stock/overseas: 스페이스X IPO valuation
  - realestate/lease: 서울 고액 월세
  - stock/ETF: 국내 ETF 순자산 500조
  - politics/policy: 부산 피란수도 세계유산 등재
  - crypto/bitcoin: 비트코인 7.3만달러대 정체
  - entertainment/K-pop: 월드컵 하프타임 쇼/K-pop
  - sports/soccer: 보은 김용식배 축구대회
  - stock/overseas: 스노우플레이크 실적/주가

Post-fix regression gates:

```bash
PYTHONPATH=apps/summarizer .venv/bin/python -m pytest \
  apps/summarizer/tests/test_step3_editorial_category.py \
  apps/summarizer/tests/test_step4_contract.py \
  apps/summarizer/tests/test_pipeline_file_selection.py \
  apps/summarizer/tests/test_common_retry.py -q
# 22 passed

cd apps/backend && PYTHONPATH=. uv run pytest \
  tests/test_article_ingest_service.py \
  tests/test_article_ingest_classification_quality.py \
  tests/test_run_news_pipeline_job.py -q
# 38 passed

python3 -m unittest tests/test_scheduled_artifact_pipeline.py tests/test_local_compose.py -q
# Ran 13 tests: OK

.venv/bin/python -m pytest tests/test_evaluate_fixed_summary_variants.py -q
# 4 passed

git diff --check
# passed
```

Interpretation:
- The expensive fresh LLM run validated the intended editorial-category improvement: post-fix, 10/10 usable imports classify through `editorial_category`.
- The run also exposed and fixed an over-strict Korean topic-mismatch guard, converting a live quality finding into regression tests.

## 2026-05-31 prompt-first topic-mismatch verifier pass

Prompting technique applied:
- Researched few-shot prompting as in-context demonstrations: Prompt Engineering Guide describes few-shot prompting as providing demonstrations in the prompt to steer model behavior on subsequent examples.
- Applied that to the verifier instead of adding more import-side token rules.
- Added checklist-style internal verification order: compare source title topic, source body topic, generated summary topic, then judge whether they are the same event.
- Added few-shot boundary examples directly in the verifier prompt:
  - `허웅 전 연인 명예훼손 재판` summarized as `무인창고 현금 68억` -> `suspicious` even if the original title term is appended later.
  - 부산 세계유산 wording variation -> `clean`.
  - 보은 김용식배 축구대회 wording variation -> `clean`.

Code direction:
- Step 4 inline verifier, Step 5 verifier, and `news_service.py` verifier now carry the same topic-mismatch prompt contract.
- The backend no longer hard-drops verifier-clean summaries solely because the token-overlap heuristic says topic mismatch. This keeps the quality path LLM-first and avoids false positives from Korean particles/compound nouns.
- Existing token-overlap helper tests remain as historical regression coverage, but import gating now follows verifier verdict/confidence/violations/retry limits rather than a standalone hard topic rule.

Fresh product-like rerun after prompt-first change:
```text
archive_report_path=/Users/reddit/Project/cut-news/apps/summarizer/data/run_reports/run_2026-05-31T004555+0900.json
status=success
failed_step=null
started_at=2026-05-31T00:45:55+0900
finished_at=2026-05-31T01:05:53+0900
feed_date=2026-05-31
max_articles=null
summarize duration=1194.834s
import_inserted=0
import_updated=10
usable_imports=10
drop_reason_counts={}
quality_warnings=[]
classification_source_counts={"editorial_category":10}
snapshot attempted=3/generated=3/failed=0
report-check failures=[]
```

Manual artifact review:
- 10/10 verified articles returned `verdict=clean`.
- verifier confidence range: 96-100.
- 10/10 summaries had `_violations=[]`.
- 10/10 usable imports classified via LLM editorial taxonomy.
- Spot-checked categories remained semantically coherent: politics/diplomacy, lifestyle/health, stock/unlisted, realestate/lease, stock/ETF, lifestyle/travel, crypto/bitcoin, entertainment/K-pop, sports/soccer, stock/overseas.

Post-pass gates:
```bash
PYTHONPATH=apps/summarizer uv run pytest \
  apps/summarizer/tests/test_step3_editorial_category.py \
  apps/summarizer/tests/test_step4_contract.py \
  apps/summarizer/tests/test_step5_verify_contract.py \
  apps/summarizer/tests/test_common_retry.py -q
# 17 passed

cd apps/backend && PYTHONPATH=. uv run pytest \
  tests/test_article_ingest_service.py \
  tests/test_run_news_pipeline_job.py -q
# 36 passed

uv run pytest tests/test_scheduled_artifact_pipeline.py tests/test_evaluate_fixed_summary_variants.py -q
# 9 passed

make local-report-check REPORT_CHECK_ARGS=--require-uncapped
# failures=[]

git diff --check
# passed
```

Presentation framing:
- We deliberately reduced rule-based hard drops after live false positives.
- The final quality story is stronger for a presentation: not “we kept adding Korean token heuristics”, but “we moved ambiguous semantic judgment into the LLM verifier, used few-shot boundary examples, and verified with a full product-like rerun.”

## 2026-05-31 fresh crawler all-category quality pass

Fresh crawl command shape:
```bash
HOME=/Users/reddit \
DATABASE_URL="sqlite+pysqlite:///$PWD/apps/backend/dev-quality-fresh-crawl-20260531-013222.db" \
SEED_ON_STARTUP=false \
NEWS_SOURCE=naver-all-categories \
NEWS_COUNT=1 \
NEWS_PIPELINE_MAX_ARTICLES= \
PIPELINE_LLM_BACKEND=hermes_cli \
PIPELINE_HERMES_PROFILE=cut-news-pipeline \
PIPELINE_MAX_WORKERS=3 \
PIPELINE_SELECTED_PER_CATEGORY=3 \
PIPELINE_BEST_OF_N=3 \
PIPELINE_BEST_OF_SCORE_THRESHOLD=80 \
make local-pipeline
make local-report-check REPORT_CHECK_ARGS=--require-uncapped
```

Run result:
```text
archive_report_path=/Users/reddit/Project/cut-news/apps/summarizer/data/run_reports/run_2026-05-31T013226+0900.json
status=success
failed_step=null
started_at=2026-05-31T01:32:26+0900
finished_at=2026-05-31T01:54:26+0900
source=naver-all-categories
count_per_query=1
crawler collected_count=42, deduped_count=7, query_count=49
json/scored/summarized/verified artifacts=10/10/10/10
import_inserted=10
usable_imports=10
drop_reason_counts={}
quality_warnings=[]
classification_source_counts={"editorial_category":10}
report-check failures=[]
```

Manual quality review:
- verifier verdict: 10/10 `clean`.
- verifier confidence range: 98-99; average 98.3.
- `_violations=[]` for all 10.
- hallucinations list empty for all 10.
- headline/summary length contract passed for all 10.
- Imported disposable DB categories: politics/domestic 4, stock/domestic 3, lifestyle/health 2, tech/startup 1.

Important coverage from this fresh crawl:
- Several crawler source-query labels were misleading, but Step 3 editorial taxonomy corrected them before import:
  - `entertainment/드라마` -> `lifestyle/health`: 차인표 푸시업/중년 운동 article.
  - `realestate/전세` -> `politics/domestic`: 정명근 화성시장 campaign article.
  - `realestate/상업용` -> `stock/domestic`: LG Group stock surge article.
  - `stock/코스피` -> `politics/domestic`: 양향자 경기지사 campaign article.
  - `sports/야구` -> `lifestyle/health`: 브라이스 하퍼 toothpaste/oral-health article.
  - `economy/GDP` -> `stock/domestic`: 한화에어로스페이스 export/stock-growth article.

Interpretation:
- This pass specifically exercised the failure mode where crawler search metadata is broad or misleading. The current LLM editorial category route overrode those weak labels and all imports used `editorial_category` rather than source-query or broad keyword fallback.
- Snapshot generation was 0 because this run used a fresh disposable SQLite DB without seeded user preferences; it is not a summary/category quality failure.

## Remaining limitations / next evidence to collect

1. Expand the fixed-article eval set from 2 articles to 10-15 representative articles.
2. Add more fixture cases for finance/company articles that should not be routed solely by company sector.
3. Revisit legacy direct Codex comparison only after OAuth is repaired; daily operation does not depend on it.

## Reusable slide bullets

- Built a disposable DB quality lane so production data was not mutated during audits.
- Added report gates for uncapped product-like runs, drop reasons, quality warnings, and snapshot generation.
- Converted manual category bugs into regression fixtures.
- Replaced brittle keyword-first classification with auditable LLM editorial category + evidence-backed fallbacks.
- Added category-balanced candidate selection to reduce LLM runtime/cost.
- Added selective best-of only for high-score articles to concentrate quality spend.
- Evaluated model/effort choices on fixed articles; selected `gpt-5.5 medium` based on repeat stability, not intuition.
- Tightened prompts against metadata leakage and meta narration in short bulletins.
- Moved ambiguous topic-mismatch judgment from token heuristics into an LLM verifier with checklist-style review and few-shot boundary examples.
