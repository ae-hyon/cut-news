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
1. Run one real Naver pipeline smoke with credentials before calling scheduled scraping production-stable:
   - `NAVER_CLIENT_ID=... NAVER_CLIENT_SECRET=... NEWS_SOURCE=naver-search NEWS_QUERY=경제 NEWS_COUNT=20 RUN_ON_STARTUP=true make full-up`
   - verify `apps/summarizer/data/run_report.json`, one `apps/summarizer/data/run_reports/run_*.json`, imported DB articles, and the new `drop_reason_counts` / `classification_source_counts` fields.
2. If content volume is still low, use `drop_reason_counts.category_unmapped`, `quality_gate:*`, and `classification_source_counts` to decide whether to tune step-3 scoring/selection, category aliasing, or verification confidence thresholds.
3. A stale shell environment can still override `FRONTEND_APP_URL` to `http://127.0.0.1:5173`; unset it or set it to `http://127.0.0.1:3000` before local backend runtime checks.

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
