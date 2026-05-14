# Cut News

뉴스 수집, 요약, 개인화 피드를 제공하는 프로젝트입니다.

## 바로 실행: 백엔드

Docker만 켜져 있으면 추가 설정 없이 백엔드 API와 Postgres를 실행할 수 있습니다.

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
curl http://127.0.0.1:8000/health
open http://127.0.0.1:8000/docs
```

중지:

```bash
make backend-down
```

DB까지 초기화:

```bash
make backend-reset
```

## 백엔드 구성

`apps/backend/docker-compose.yml`은 다음만 띄웁니다.

- `api`: FastAPI backend, `http://127.0.0.1:8000`
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

루트 `docker-compose.yml`은 백엔드 외에 crawler와 daily scheduler까지 함께 띄웁니다.

```bash
make full-up
```

포함 서비스:
- backend API: `http://127.0.0.1:8000`
- crawler API: `http://127.0.0.1:8001`
- news scheduler: 매일 `08:30` Asia/Seoul 기준으로 crawler -> summarizer -> backend import 실행
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
make pipeline-news NEWS_SOURCE=naver-search NEWS_QUERY=경제 NEWS_COUNT=20
```
