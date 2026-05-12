# Annoying Cap Core Backend

Annoying Cap의 메인 서비스 백엔드입니다.

현재 상태:
- FastAPI 기반
- local Postgres + Docker Compose 사용
- DDD + layered architecture 구조
- domain/application/infrastructure/presentation 분리
- sibling 프로젝트 `../summarizer`의 `data/json`, `data/summarized`, `data/category_map.json`를 읽어 뉴스 홈 데이터를 seed
- summarizer ingest는 경제성 title signal 또는 신뢰 가능한 source subcategory가 있는 기사만 backend taxonomy로 매핑하고, 최신 import 결과에 없는 기존 `SUM-*` 기사는 stale 데이터로 정리함
- summary gateway가 API schema -> summarizer schema typed boundary를 거치도록 정리됨
- `/v1/auth/session`, `/v1/auth/kakao/start`, `/v1/auth/kakao/callback`, `/v1/auth/refresh`, `/v1/auth/logout` API 경계 제공
- Kakao `provider_subject -> internal user_id` 매핑 저장소가 추가됨
- Kakao OAuth state는 JWT 서명 토큰으로 발급/검증함
- access token은 JWT, refresh token은 DB 저장소 기반으로 운용
- refresh token 원문은 DB에 저장하지 않고 SHA-256 hash + session metadata로 관리
- `GET /v1/auth/kakao/callback`은 인증 완료 후 `FRONTEND_APP_URL/?auth=kakao`로 302 redirect하고 HttpOnly 쿠키를 설정함
- 프론트는 `session_state` (`authenticated` / `onboarded`)와 저장된 preference를 보고 자체 라우팅하면 됨
- 온보딩 validation은 backend가 보장: wide=대분류 3~5개/중복 금지/subcategory 금지, narrow=대분류 1개 + subcategory 1개 이상/중복 금지
- 피드 블록 정책은 Flow.pdf 기준으로 backend가 보장: wide=선택 순서대로 블록 구성 + 가중치 1.0/0.85/0.70... + 블록당 최대 4개 기사, narrow=단일 focus block weight 1.0 + 선택 subcategory 부족 시 같은 primary 기사로 4개까지 fallback 채움 + 같은 날짜/같은 대분류의 유사 제목 기사는 중복 제거 + score_weight 0.65 미만 기사는 feed에서 제외
- auth application 영역은 `app/application/auth/` 하위로 분리됨
- domain 모델은 dataclass 대신 Pydantic으로 통일
- schema 관리는 Alembic migration 기반, startup 시 migration + seed 수행


기준 문서:
- `../어노잉캡-Flow.pdf`
- `../summarizer`

## Requirements

- Python 3.11
- Docker / Docker Compose
- `../summarizer` 디렉터리 존재

## Project structure

```text
app/
  main.py
  common/
    config.py
  domain/
    entities.py
    enums.py
    exceptions.py
    repositories.py
  application/
    auth/
      errors.py
      kakao_oauth_service.py
      query_service.py
      state_service.py
      token_service.py
    services/
      auth_service.py
  infrastructure/
    database.py
    models.py
    repositories.py
    seed.py
  presentation/
    api/
      router.py
      routes/
    schemas.py
docker-compose.yml
.env.example
.env
pyproject.toml
README.md
```

레이어 역할:
- domain: 핵심 모델, enum, 예외, repository interface
- application: 유스케이스/서비스 orchestration
- infrastructure: SQLAlchemy, DB session, repository 구현, seed
- presentation: FastAPI router, dependency, request/response schema

## Environment

기본 환경 파일:

```bash
cp .env.example .env
```

기본값:

```env
APP_ENV=development
APP_NAME=Annoying Cap Core Backend
APP_VERSION=0.1.0
API_PREFIX=/v1
FRONTEND_APP_URL=http://127.0.0.1:5173
DEBUG=true
DATABASE_ECHO=false
MIGRATE_ON_STARTUP=true
SEED_ON_STARTUP=true
DATABASE_URL=postgresql+psycopg://annoyingcap:annoyingcap@localhost:54329/annoyingcap
NEWS_SUMMARIZER_DIR=../summarizer
KAKAO_REST_API_KEY=...
KAKAO_REDIRECT_URI=http://127.0.0.1:8000/v1/auth/kakao/callback
KAKAO_CLIENT_SECRET=...
KAKAO_TOKEN_URL=https://kauth.kakao.com/oauth/token
KAKAO_USERINFO_URL=https://kapi.kakao.com/v2/user/me
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_MINUTES=30
JWT_REFRESH_TOKEN_DAYS=14
OAUTH_STATE_TTL_MINUTES=10
AUTH_ACCESS_COOKIE_NAME=annoyingcap_access_token
AUTH_REFRESH_COOKIE_NAME=annoyingcap_refresh_token
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
```
```







주의:
- `NEWS_SUMMARIZER_DIR`는 `data/json`, `data/summarized`, `data/category_map.json`가 있는 `apps/summarizer` 디렉터리를 가리켜야 합니다.
- 현재 startup 시 `MIGRATE_ON_STARTUP=true`이면 Alembic `upgrade head`가 먼저 실행됩니다.
- 현재 startup 시 `SEED_ON_STARTUP=true`이면 seed 데이터가 idempotent 하게 주입됩니다.
- `NEWS_SUMMARIZER_DIR/data`에 요약 결과가 있으면 그 데이터를 우선 주입하고, 없으면 backend fallback seed를 사용합니다.
- 서버 기동 후 요약 결과를 다시 반영하려면 `PYTHONPATH=. python3.11 -m app.scripts.import_articles_from_summarizer`를 실행합니다. 같은 id 또는 같은 `original_url`은 새로 추가하지 않고 update 합니다.
## Install

현재 환경에 필요한 주요 패키지:

```bash
uv sync --all-extras
```

수동 설치가 필요한 경우:

```bash
python3.11 -m pip install \
  'fastapi>=0.115,<0.116' \
  'uvicorn[standard]>=0.32,<1' \
  'httpx>=0.28,<0.29' \
  'sqlalchemy>=2,<3' \
  'psycopg[binary]>=3.2,<4' \
  'pydantic-settings>=2.6,<3' \
  'alembic>=1.13,<2' \
  'PyJWT>=2.8,<3'
```

## Run locally with Docker

새 환경에서는 Docker Compose만으로 Postgres와 backend API를 함께 실행할 수 있습니다.

```bash
cd apps/backend
docker compose up --build
```

검증:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/openapi.json
curl 'http://127.0.0.1:8000/v1/users/demo-user/feed'
curl 'http://127.0.0.1:8000/v1/users/demo-user/scraps'
```

`docker compose up --build`로 뜨는 DB는 startup migration 이후 seed가 자동 실행됩니다.
프론트 테스트용으로 별도 크롤링/수집 작업을 실행하지 않아도 바로 사용할 수 있습니다.
기본 seed에는 git에 포함된 `apps/summarizer/data` 샘플 기사와 backend 내장 mock 기사, `demo-user` 관심사, 예시 스크랩 2개가 포함됩니다.

Swagger UI:

```bash
open http://127.0.0.1:8000/docs
```

중지:

```bash
docker compose down
```

DB volume까지 초기화하려면:

```bash
docker compose down -v
```

## Run locally without Docker

1) Postgres 실행

```bash
docker compose up -d
```

2) 필요한 경우 수동 migration 실행

```bash
python3.11 -m alembic upgrade head
```

3) 서버 실행

```bash
python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

4) 헬스체크

```bash
curl http://127.0.0.1:8000/health
```

예상 응답:

```json
{"status":"ok","app":"Annoying Cap Core Backend","version":"0.1.0"}
```

## Main APIs

- `GET /health`
- `GET /v1/categories`
- `GET /v1/categories/{slug}`
- `GET /v1/auth/session`
- `GET /v1/auth/kakao/start`
- `GET /v1/auth/kakao/callback`
- `POST /v1/auth/refresh`
- `POST /v1/auth/logout`
- `GET /v1/users/{user_id}/preferences`
- `PUT /v1/users/{user_id}/preferences`
- `GET /v1/users/{user_id}/feed`
- `GET /v1/articles/{article_id}`
- `PUT /v1/users/{user_id}/scraps/{article_id}`
- `DELETE /v1/users/{user_id}/scraps/{article_id}`
- `GET /v1/users/{user_id}/scraps`
- `POST /v1/summaries`

## Example requests

카테고리 목록:

```bash
curl http://127.0.0.1:8000/v1/categories
```

인증 상태 확인:

```bash
curl 'http://127.0.0.1:8000/v1/auth/session?user_id=demo-user'
curl 'http://127.0.0.1:8000/v1/auth/session?provider=kakao&provider_subject=runtime-kakao-001'
curl --cookie 'annoyingcap_access_token=...' 'http://127.0.0.1:8000/v1/auth/session'
```

Kakao 로그인 시작 URL 생성:

```bash
curl 'http://127.0.0.1:8000/v1/auth/kakao/start'
```

Kakao callback 처리 확인:

브라우저에서 Kakao 로그인 버튼을 통해 확인하세요. callback은 성공 시 `FRONTEND_APP_URL/?auth=kakao`로 302 redirect하고 access/refresh 쿠키를 설정합니다.

주의:
- OAuth code/state는 1회용입니다. callback URL을 새로고침하지 말고 로그인 버튼에서 새 flow를 시작하세요.
- 로컬에서는 frontend/backend/Kakao redirect URI를 모두 `127.0.0.1` 기준으로 맞추는 것을 권장합니다.

토큰 재발급:

```bash
curl -X POST --cookie 'annoyingcap_refresh_token=...' http://127.0.0.1:8000/v1/auth/refresh
```

로그아웃:

```bash
curl -X POST --cookie 'annoyingcap_refresh_token=...' http://127.0.0.1:8000/v1/auth/logout
```

사용자 선호 업데이트:

```bash
curl -X PUT http://127.0.0.1:8000/v1/users/demo-user/preferences \
  -H 'Content-Type: application/json' \
  -d '{
    "mode": "narrow",
    "primary_categories": ["economy"],
    "subcategories": ["real-estate", "macro"]
  }'
```

온보딩 규칙:
- wide: `primary_categories` 3~5개, 중복 금지, `subcategories` 비어 있어야 함
- narrow: `primary_categories` 정확히 1개, `subcategories` 1개 이상, 둘 다 중복 금지
- 유효한 선호 저장이 완료되면 `onboarding_completed=true`

요약 생성:

```bash
curl -X POST http://127.0.0.1:8000/v1/summaries \
  -H 'Content-Type: application/json' \
  -d '{
    "article": {
      "title": "말레이시아서 한국인 남성 납치 4일 만에 구조, 범인도 한국인",
      "date": "2026-04-27",
      "author": "기자",
      "content": "말레이시아에서 한국인 남성이 납치됐다가 4일 만에 구조됐다. 현지 경찰은 용의자로 한국인 일당을 체포해 조사 중이다."
    },
    "verify": false,
    "max_retries": 1,
    "backend": "codex_exec",
    "model": "gpt-5.4-mini",
    "reasoning_effort": "low",
    "timeout": 300
  }'
```

## Verified status

현재 로컬 검증 완료:
- Python compile 통과
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m alembic upgrade head` 통과
- 실제 주요 엔드포인트 200 응답 확인
- `GET /v1/auth/kakao/start` authorization URL 응답 확인
- `GET /v1/auth/session`의 anonymous / onboarded / authenticated 상태 확인
- JWT access cookie 기반 `GET /v1/auth/session` authenticated 상태 확인
- `POST /v1/auth/refresh` access/refresh cookie rotation 확인
- `POST /v1/auth/logout` cookie clear 확인
- `GET /v1/auth/kakao/callback` JSON 응답 + `HttpOnly` cookie 동작은 TestClient로 검증
- `external_identities`, `refresh_sessions` migration 및 DB-backed auth 검증 확인
- refresh token hash 저장 및 `issued_at` / `last_used_at` / `revoked_at` metadata migration 확인
- `/v1/summaries`가 `../summarizer` 연동으로 정상 동작 확인
- domain dataclass 제거, Pydantic 기반 모델로 통일 완료
- onboarding validation: wide/narrow 규칙 및 중복 금지 contract 테스트로 검증
- feed weighting: 선호 순서 보존, block weight 하향, article 중요도 점수 단독 정렬, wide 4개 노출, narrow same-primary fallback 검증

## Tests

```bash
PYTHONPATH=. python3.11 -m pytest tests -q
python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')
```

## Notes

- 현재는 Alembic migration + startup seed 조합을 사용합니다.
- 기존 pre-Alembic 로컬 DB가 있으면 startup 시 `alembic_version`을 head로 stamp 해서 호환합니다.
- 이후 실제 운영 단계에서는 seed 전략을 환경별로 더 분리하는 것이 좋습니다.
- 프로젝트 명칭은 PDF 기준으로 `Annoying Cap`을 사용합니다.
- 개인화/고도화 항목(사용자 반응 기반 피드 weight, 행동 로그 기반 추천, summary 운영 플로우 정교화)은 의도적으로 후순위 백로그로 남겨두었습니다.
