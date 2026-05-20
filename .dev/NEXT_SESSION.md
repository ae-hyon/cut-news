# Next session handoff

## Current branch
- `main`
- synced with `origin/main`
- latest origin/main commit: run `git log -1 --oneline origin/main` after fetch/pull

## Recently merged / landed work
- #33 `feat(frontend): 프론트엔드 초기 UI 구현`
- #34 `fix: stabilize crawler ids and safe stale import pruning`
- #35 `fix: gate low-quality summarizer imports`
- #36 `feat: add pipeline run report wrapper`
- #38 `feat(frontend): 카카오 로그인 연동 및 인증 인프라 구성`
- #39 `fix: 카카오 로그인 쿠키/CORS 문제 해결 및 직접 통신 전환`
- direct/main follow-ups:
  - `8050f76 fix: resolve PR 33 merge conflicts`
  - `cb49b5d fix: require auth for article detail`
  - `a9f14f0 docs: simplify backend docker workflow`

## Done in the latest slice
- Updated local backend/frontend auth wiring for the real Next frontend on port `3000`.
- Backend now treats `http://127.0.0.1:3000` as the frontend origin by default:
  - `apps/backend/app/common/config.py`
  - `apps/backend/docker-compose.yml`
- Backend adds CORS middleware with `allow_credentials=True` so browser cookie auth works cross-origin from frontend `3000` to backend `8000`.
- Frontend no longer proxies `/v1/*` through Next rewrites; it calls backend directly through `API_BASE`:
  - default `NEXT_PUBLIC_API_URL || http://127.0.0.1:8000`
  - file: `apps/frontend/src/lib/api.ts`
- Next config now keeps only the crawler rewrite:
  - `/api/crawler/:path* -> http://localhost:8001/:path*`
- Article detail route now requires authenticated current-user context instead of exposing the user-scoped detail contract anonymously.
- Pipeline run report wrapper persists `quality_gate_skip_counts` and now also writes timestamped archives:
  - `apps/summarizer/data/run_report.json`
  - archive: `apps/summarizer/data/run_reports/run_*.json`
  - report observability now includes `quality_gate_skip_counts`, `drop_reason_counts`, and `classification_source_counts` so low imported volume can be attributed to quality gates, missing outputs/fields, category mapping failures, or source-vs-keyword classification.
- News scheduler now retries failed pipeline runs with `PIPELINE_MAX_ATTEMPTS` / `PIPELINE_RETRY_DELAY_SECONDS`; `RUN_ON_STARTUP=true` fails fast if the startup smoke cannot succeed after retries.

- FastAPI OpenAPI docs were upgraded for frontend/backend contract validation:
  - app-level docs call out real Next frontend `3000`, `credentials: include`, and deprecated `apps/test-frontend`.
  - protected routes expose `AccessTokenCookie` cookie auth in Swagger/OpenAPI.
  - auth/session/feed/preference/article/scrap routes now include actionable summaries/descriptions and 401/404/422 response notes.
  - key schemas include examples for session states, preference update payloads, and feed shape.
  - tests cover the OpenAPI contract in `apps/backend/tests/test_openapi_frontend_contract.py`.
- Phase 5 snapshot archive API is implemented:
  - `GET /v1/me/archive?month=YYYY-MM` lists persisted snapshot days only and no longer recalculates runtime current-preference archive items.
  - `GET /v1/me/archive/{YYYY-MM-DD}` reads persisted snapshot items in snapshot sort order, marks the snapshot viewed/check-in, and includes snapshot metadata plus read counts.
  - Archive response schemas expose `snapshot_id`, `status`, `has_feed`, `read_count`, `total_count`, `first_viewed_at`, and `completed_at`; daily archive preserves article cards and current `is_scrapped` state.
- Phase 6 read tracking is implemented:
  - `GET /v1/articles/{article_id}` and `GET /v1/me/articles/{article_id}` mark authenticated article-detail opens as read.
  - Detail routes accept optional `snapshot_id` query; with a snapshot context, read state contributes to snapshot `read_count` and completion.
  - Detail opens without `snapshot_id` are allowed and stored as article-only reads without changing any snapshot status.
  - Re-reading the same article in the same snapshot is idempotent; when all snapshot items are read, the snapshot is saved as `completed` with `completed_at`.
  - Current scrap state remains separate from read state and is still returned as `is_scrapped`.
- Phase 7 scheduler snapshot generation is implemented:
  - After a successful import step, `run_news_pipeline_job` generates today's snapshot for onboarded users using the configured schedule timezone.
  - Import failure or earlier step failure skips snapshot generation.
  - Per-user snapshot failures are counted in `snapshot_generation.failed_count` and do not fail the whole pipeline.
  - `run_report.json` and archived `run_reports/run_*.json` include `feed_date` and `snapshot_generation` counters: `attempted_user_count`, `generated_count`, `skipped_viewed_count`, `failed_count`.

## Current runtime ports
- Backend API: `http://127.0.0.1:8000`
- Real Next frontend: `http://127.0.0.1:3000`
- `apps/test-frontend` / Vite `5173` is deprecated and should not be used for the next backend work.
- Crawler API when used locally: `http://127.0.0.1:8001`
- Backend Postgres Docker host port: `54329`

## Current repo state
- current checkout: `main`
- synced with `origin/main`
- current HEAD: run `git log -1 --oneline`
- local-only untracked artifacts currently observed:
  - `어드민잉캡-Flow.pdf`
  - `경제_뉴스_클레이션_PRD.docx`
- `apps/summarizer/data/classification_cache.json` was mentioned in the old handoff but is not currently present.

## Most relevant files now
- Backend runtime/config:
  - `apps/backend/app/common/config.py`
  - `apps/backend/app/main.py`
  - `apps/backend/docker-compose.yml`
  - `apps/backend/app/presentation/api/routes/auth.py`
  - `apps/backend/app/presentation/api/routes/articles.py`
- Real frontend:
  - `apps/frontend/src/lib/api.ts`
  - `apps/frontend/src/hooks/useKakaoLogin.ts`
  - `apps/frontend/src/services/authApi.ts`
  - `apps/frontend/src/stores/auth.ts`
  - `apps/frontend/next.config.ts`
- Do not modify `apps/frontend` unless explicitly requested; another developer owns frontend implementation. Use these files only to understand the backend-facing contract.
- Pipeline/reporting:
  - `apps/backend/app/scripts/run_news_pipeline_job.py`
  - `apps/backend/app/scripts/import_articles_from_summarizer.py`
  - `apps/backend/app/application/services/article_ingest_service.py`
- `apps/test-frontend/` is legacy/deprecated and should not be treated as the source of truth.

## Working policy from the user
- Backend and real Next frontend must stay contract-synced.
- Frontend code is owned by another developer; do not edit frontend unless explicitly asked.
- Backend-side focus is article ingestion/retrieval quality and clear auth/authorization boundaries.
- Prefer backend tests/API contract checks over test-frontend flows.

## Verification known from current tree
- Latest main update was a fast-forward from `a9f14f0` to `a2230be`.
- Files changed by latest commit:
  - `apps/backend/app/common/config.py`
  - `apps/backend/app/main.py`
  - `apps/backend/docker-compose.yml`
  - `apps/frontend/next.config.ts`
  - `apps/frontend/src/hooks/useKakaoLogin.ts`
  - `apps/frontend/src/lib/api.ts`
- Live servers were not restarted during this handoff update. Re-verify runtime manually before assuming the local browser session reflects current files.

## Remaining mismatches / next best slice
1. Product direction for `나의 뉴스 피드` / monthly archive is now snapshot-based, not runtime current-preference filtering.
   - Source workflow doc: `.dev/news-feed-archive-workflow.md`
   - Development checklist: `.dev/news-feed-snapshot-development-checklist.md`
2. Snapshot phases 1-7 are complete:
   - Phase 1: daily feed snapshot/read entities, SQLAlchemy models, Alembic migration, repository protocols, repository implementation, and repository tests.
   - Phase 2: `FeedService.get_feed()` delegates to reusable `build_feed_blocks_for_preference(...)`, with wide/narrow selector coverage.
   - Phase 3: `DailyFeedSnapshotService` generates/regenerates unviewed snapshots, preserves viewed snapshots, freezes preference-at-generation and block item metadata, and delegates view/read state.
   - Phase 4: `GET /v1/me/feed` lazy-generates today's Asia/Seoul snapshot, marks it viewed, and returns required snapshot metadata plus preserved `mode`/`blocks[].articles` card shape.
   - Phase 5: monthly/daily archive endpoints use persisted snapshots, include snapshot/read metadata, mark daily archive opens viewed, and preserve snapshot item article cards with current scrap state.
   - Phase 6: authenticated article detail opens mark read; optional `snapshot_id` query links reads to snapshot completion; article-only reads are allowed and do not complete snapshots.
   - Phase 7: successful scheduler/import runs generate daily snapshots for onboarded users and persist `run_report.snapshot_generation` counters.
3. Phase 8 docs/API contract is complete:
   - `apps/backend/README.md` documents `/v1/me/feed`, `/v1/me/archive?month=YYYY-MM`, `/v1/me/archive/{YYYY-MM-DD}`, read tracking, status transitions, calendar mapping, and scheduler `run_report.snapshot_generation` fields.
   - `.dev/news-feed-archive-workflow.md` now reflects implemented snapshot-backed API behavior instead of the old runtime preference-filtered archive.
   - OpenAPI schema docs/examples were tightened for feed/archive snapshot fields.
4. Phase 9 full verification is complete:
   - `make test`: `114 passed`.
   - Root compose API was rebuilt with current backend image via `docker compose up -d --build api`.
   - `api` and `db` are healthy; `/health` and `/v1/categories` smoke checks pass.
   - DB migration smoke shows `alembic_version=0006_daily_feed_snapshots` and all three snapshot/read tables exist.
5. Next best slice: cleanup/PR preparation.
   - Separate real source/doc changes from generated summarizer data churn before committing.
   - Naver pipeline smoke is still useful later, but snapshot development should not be blocked by real Naver credentials.
6. A stale shell environment can still override `FRONTEND_APP_URL` to `http://127.0.0.1:5173`; unset it or set it to `http://127.0.0.1:3000` before local backend runtime checks.

## Suggested first commands next session
```bash
cd /Users/reddit/Project/cut-news
git status --short --branch
git log --oneline -5
curl -sf http://127.0.0.1:8000/health || true
curl -sf http://127.0.0.1:3000 | head -n 3 || true
```

Backend Docker:
```bash
make backend-up
```

Real frontend:
```bash
pnpm dev:frontend
```

Backend tests:
```bash
make test
```
