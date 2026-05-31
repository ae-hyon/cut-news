# Cut News

뉴스 수집, 요약, 개인화 피드를 제공하는 프로젝트입니다.

## 바로 실행: 전체 앱

Docker만 켜져 있으면 실제 Next 프론트, 백엔드 API, crawler, scheduler, Postgres를 한 번에 실행할 수 있습니다.

```bash
make full-up
```

실행 후 확인:

```bash
open http://127.0.0.1:3030
curl http://127.0.0.1:8030/health
open http://127.0.0.1:8030/docs
```

포트:
- frontend: `http://127.0.0.1:3030`
- backend API: `http://127.0.0.1:8030`
- crawler API: `http://127.0.0.1:8001`
- Postgres: host port `54329`

중지:

```bash
make full-down
```

## 바로 실행: 백엔드만

Docker만 켜져 있으면 추가 설정 없이 백엔드 API와 Postgres만 실행할 수 있습니다.

```bash
make backend-up
```

직접 실행하려면:

```bash
cd apps/backend
docker compose up --build
```

실행 후 확인:

```bash
curl http://127.0.0.1:8030/health
open http://127.0.0.1:8030/docs
```

중지:

```bash
make backend-down
```

DB까지 초기화:

```bash
make backend-reset
```

## 선택: 외부 Postgres / Neon 사용

공유 개발 DB나 간단한 staging DB가 필요하면 Supabase 대신 Neon Postgres를 권장합니다. 기존 SQLAlchemy/Alembic/Postgres 구조를 그대로 쓰므로 코드 변경 없이 `DATABASE_URL`만 바꾸면 됩니다.

1. Neon에서 project/database를 만들고 pooled connection string을 복사합니다.
2. 루트 `.env`에 `DATABASE_URL`을 추가합니다. 비밀번호는 commit하지 않습니다.

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/DB?sslmode=require
```

3. migration을 먼저 적용합니다.

```bash
make db-migrate
make db-current
```

4. Dockerless local compose 또는 로컬 pipeline을 실행합니다.

```bash
make local-up SERVICES="backend crawler scheduler"
make local-pipeline
```

주의:
- Neon은 앱 runtime에는 pooled URL을 우선 사용합니다.
- `make backend-up` / `make full-up`도 루트 `.env`의 `DATABASE_URL`을 컨테이너에 전달하지만, 로컬 Postgres 컨테이너는 개발 기본 구성으로 함께 뜰 수 있습니다. 외부 DB만 쓰는 smoke에는 `make local-up`이 더 단순합니다.
- 테스트(`make test`)는 외부 DB가 아니라 repo 기본 test DB를 사용합니다.

## 백엔드 구성

`apps/backend/docker-compose.yml`은 다음만 띄웁니다.

- `api`: FastAPI backend, `http://127.0.0.1:8030`
- `db`: Postgres 16, host port `54329`

컨테이너 시작 시 migration과 seed가 자동 실행됩니다. `apps/summarizer/data`에 샘플 요약 데이터가 있으면 기사 seed에 사용하고, 없으면 backend fallback seed를 사용합니다.

Kakao 실로그인은 Kakao 앱 키가 있어야 하지만, 서버 기동/health/docs/categories 확인에는 별도 `.env`가 필요 없습니다.

## 주요 API

Public:
- `GET /health`
- `GET /v1/categories`
- `GET /v1/categories/{slug}`

Auth:
- `POST /v1/auth/oauth/kakao/authorization`
- `GET /v1/auth/oauth/kakao/callback`
- `POST /v1/auth/token/refresh`
- `DELETE /v1/auth/session`

로그인 필요:
- `GET /v1/me`
- `GET /v1/me/preference`
- `PUT /v1/me/preference`
- `GET /v1/me/feed`
- `GET /v1/articles/{article_id}`
- `GET /v1/me/articles/{article_id}`
- `GET /v1/me/scraps`
- `PUT /v1/me/scraps/{article_id}`
- `DELETE /v1/me/scraps/{article_id}`

Internal:
- `POST /v1/internal/summaries`

## 테스트

```bash
make test
```

또는:

```bash
cd apps/backend
PYTHONPATH=. uv run pytest tests/ -q
```

## 선택: 전체 뉴스 파이프라인

권장 로컬 실행은 Dockerless local compose입니다. AI 요약 단계가 `codex_exec` 또는 Hermes gateway처럼 호스트의 OAuth/session 기반 도구를 쓰기 때문에, Docker 컨테이너 안으로 AI CLI 인증을 전달하는 것보다 호스트에서 직접 실행하는 편이 단순합니다.

```bash
make local-up       # frontend + backend + crawler + scheduler 시작
make local-up SERVICES="backend crawler scheduler"  # frontend 제외
make local-ps       # docker compose ps 느낌의 상태 확인
make local-logs     # 로그 tail
make local-pipeline # 즉시 파이프라인 1회 실행
make local-report   # 최신 run_report 요약
make local-down     # 중지
```

`docker compose`에 익숙하면 wrapper를 직접 써도 됩니다.

```bash
./scripts/local-compose.py up -d backend crawler scheduler
./scripts/local-compose.py ps
./scripts/local-compose.py logs -f backend
./scripts/local-compose.py restart backend
./scripts/local-compose.py stop
```

포함 서비스:
- frontend: `http://127.0.0.1:3030`
- backend API: `http://127.0.0.1:8030`
- crawler API: `http://127.0.0.1:8001`
- local scheduler: 매일 `08:30` Asia/Seoul 기준으로 crawler -> summarizer -> backend import 실행. 홈 피드는 서버가 `09:00`~다음날 `02:59` KST 발행 window에서만 노출하며, `03:00`~`08:59`에는 `/v1/me/feed`가 `425 Too Early`를 반환합니다.

로그와 pid는 `.local/compose/` 아래에 저장됩니다. 기본 DB는 Docker 없이 `apps/backend/dev-ui-test.db` SQLite를 사용합니다. 루트 `.env`와 `apps/backend/.env`가 있으면 자동으로 읽습니다.

Docker Compose가 필요할 때는 루트 `docker-compose.yml`로 백엔드 외에 실제 Next 프론트, crawler, daily scheduler, Postgres까지 함께 띄울 수 있습니다.

처음 실행할 때는 루트 환경 파일을 준비합니다. 기본값(`NEWS_SOURCE=seeded`)은 Naver credential 없이 실행됩니다.

```bash
cp .env.example .env
```

Naver Search API로 실제 뉴스를 수집하려면 루트 `.env`에 다음 값을 채우고 `NEWS_SOURCE=naver-search`로 바꿉니다.

```dotenv
NEWS_SOURCE=naver-search
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
```

이 credential은 crawler 수집 로직에서 사용하며, Docker Compose에서는 `crawler`와 full pipeline 실행 주체인 `news-scheduler` 컨테이너에 함께 전달됩니다.

```bash
make full-up
```

포함 서비스:
- frontend: `http://127.0.0.1:3030`
- backend API: `http://127.0.0.1:8030`
- crawler API: `http://127.0.0.1:8001`
- news scheduler: 매일 `08:30` Asia/Seoul 기준으로 crawler -> summarizer -> backend import 실행. 홈 피드는 서버가 `09:00`~다음날 `02:59` KST 발행 window에서만 노출하며, `03:00`~`08:59`에는 `/v1/me/feed`가 `425 Too Early`를 반환합니다.
  - 실패 시 기본 2회까지 재시도합니다. (`PIPELINE_MAX_ATTEMPTS`, `PIPELINE_RETRY_DELAY_SECONDS`)
  - 최신 실행 결과는 `apps/summarizer/data/run_report.json`, 실행별 archive는 `apps/summarizer/data/run_reports/run_*.json`에 저장됩니다.
  - 실행 결과에는 `import_stats`, `quality_gate_skip_counts`, `drop_reason_counts`, `classification_source_counts`가 포함되어 몇 건이 어떤 검증/분류 단계에서 제외됐는지 확인할 수 있습니다.
- Postgres

즉시 한 번 실행하면서 띄우려면:

```bash
RUN_ON_STARTUP=true make full-up
```

중지:

```bash
make full-down
```

## 로컬 개발

Docker 없이 백엔드만 실행:

```bash
make dev-backend
```

수동 기사 import:

```bash
make import-articles
```

수동 뉴스 파이프라인 1회 실행:

```bash
make pipeline-news NEWS_SOURCE=seeded
```

Naver Search credential이 있는 경우:

```bash
cp .env.example .env
# .env에 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 입력 후 NEWS_SOURCE=naver-search 설정
make pipeline-news NEWS_QUERY=경제 NEWS_COUNT=20
```

전체 서비스 카테고리 기준으로 Naver를 수집하려면 `naver-all-categories`를 사용합니다. 이 모드에서 `NEWS_COUNT`는 전체 개수가 아니라 카테고리 키워드/중분류 쿼리당 요청 개수입니다. 상세 taxonomy와 발행/아카이브 기준 시간은 `.dev/news-pipeline-category-schedule.md`에 기록되어 있습니다. 실제 데이터 기반 검증은 `NEWS_PIPELINE_MAX_ARTICLES`를 비워 둡니다. 이 값은 LLM 처리 시간/비용을 의도적으로 제한해야 할 때만 쓰는 진단용 cap입니다.

```bash
NEWS_SOURCE=naver-all-categories NEWS_COUNT=1 make local-pipeline
make local-report
```

GitHub Actions의 `.github/workflows/crawl-naver.yml`은 크롤링만 스케줄링합니다. 매일 08:00 Asia/Seoul에 Naver 수집을 실행하고 `latest.json`, `crawl_report.json`, `github_action_crawl_summary.json`을 7일 artifact로 업로드합니다. repository secret `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET`이 필요합니다. 요약/검증/import는 Codex OAuth/session이 필요한 `codex_exec` 런타임에 의존하므로 GitHub Actions에서는 실행하지 않고 로컬 또는 Codex가 설정된 서버에서 처리합니다.

```bash
gh workflow run crawl-naver.yml -f source=naver-all-categories -f count=1
```

`Makefile`은 루트 `.env`가 있으면 자동으로 읽기 때문에, 로컬 1회 실행과 `make full-up` 모두 같은 credential 설정을 공유합니다.
