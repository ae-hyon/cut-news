# Annoying Cap Core Backend

FastAPI 기반 백엔드 API입니다.

## 바로 실행

Docker만 켜져 있으면 추가 설정 없이 API와 Postgres를 실행할 수 있습니다.

```bash
cd apps/backend
docker compose up --build
```

루트에서 실행하려면:

```bash
make backend-up
```

확인:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/v1/categories
open http://127.0.0.1:8000/docs
```

중지:

```bash
docker compose down
```

DB volume까지 초기화:

```bash
docker compose down -v
```

## Docker Compose 구성

`apps/backend/docker-compose.yml`은 백엔드 실행에 필요한 최소 구성입니다.

- `api`: FastAPI backend, `http://127.0.0.1:8000`
- `db`: Postgres 16, host port `54329`

컨테이너 시작 시 다음이 자동으로 실행됩니다.

- Alembic migration: `MIGRATE_ON_STARTUP=true`
- seed: `SEED_ON_STARTUP=true`

`NEWS_SUMMARIZER_DIR=/app/apps/summarizer` 기준으로 샘플 요약 데이터가 있으면 기사 seed에 사용하고, 없으면 backend fallback seed를 사용합니다.

Kakao 실로그인은 Kakao 앱 키가 필요합니다. 다만 서버 기동, health check, Swagger, category API 확인에는 별도 `.env`가 필요 없습니다.

## 환경 변수

일반 로컬 실행용 예시는 `.env.example`에 있습니다.

Docker Compose는 개발 기본값을 compose 파일에 넣어두었기 때문에 `.env` 없이도 뜹니다. 실로그인까지 확인할 때만 아래 값을 실제 Kakao 앱 설정에 맞춥니다.

```env
KAKAO_REST_API_KEY=...
KAKAO_CLIENT_SECRET=...
KAKAO_REDIRECT_URI=http://127.0.0.1:8000/v1/auth/oauth/kakao/callback
FRONTEND_APP_URL=http://127.0.0.1:3000
JWT_SECRET_KEY=change-this-local-dev-secret-at-least-32-chars
```

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
- `PATCH /v1/me/preference`
- `GET /v1/me/feed`
- `GET /v1/articles/{article_id}`
- `GET /v1/me/articles/{article_id}`
- `GET /v1/me/scraps`
- `PUT /v1/me/scraps/{article_id}`
- `DELETE /v1/me/scraps/{article_id}`

Internal:
- `POST /v1/internal/summaries`

## 인증/피드 계약

- 프론트는 `GET /v1/me`의 `session_state`를 보고 자체 라우팅합니다.
- `GET /v1/me`는 앱 부팅용 세션 스냅샷이며 `preference`에 현재 관심 카테고리 요약(`mode`, `primary_categories`, `subcategories`)을 함께 내려줍니다. 비로그인 상태는 `preference: null`입니다.
- `session_state`는 `anonymous`, `authenticated`, `onboarded` 중 하나입니다.
- 기사 상세, feed, scraps는 로그인된 현재 사용자 기준으로 동작합니다.
- `is_scrapped`는 현재 사용자의 스크랩 상태를 뜻합니다.

온보딩 선호 규칙:
- wide: `primary_categories` 3~5개, `subcategories` 비어 있어야 함
- narrow: `primary_categories` 정확히 1개, `subcategories` 1개 이상
- 둘 다 중복 금지

## 테스트

```bash
cd apps/backend
PYTHONPATH=. uv run pytest tests/ -q
```

루트에서:

```bash
make test
```

## 로컬 개발

Docker 없이 sqlite로 실행:

```bash
cd apps/backend
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

요약 데이터 수동 import:

```bash
cd apps/backend
PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db uv run python -m app.scripts.import_articles_from_summarizer
```
