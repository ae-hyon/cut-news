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

## 외부 Postgres / Neon

Supabase 없이 무료 managed DB를 붙일 때는 Neon Postgres를 권장합니다. Backend는 `DATABASE_URL` 하나로 DB를 선택하고, Alembic도 같은 값을 읽습니다.

루트 `.env` 또는 `apps/backend/.env`에 Neon pooled connection string을 넣습니다. 루트 `.env` 값이 Dockerless local compose와 pipeline 공유 설정의 우선값입니다.

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST.neon.tech/DB?sslmode=require
```

적용 순서:

```bash
# repo root
make db-migrate
make db-current
make local-up SERVICES="backend crawler scheduler"
```

운영 주의:
- `.env`는 commit하지 않습니다.
- Neon runtime에는 pooled URL을 우선 사용합니다.
- `make backend-up`/`make full-up`도 `DATABASE_URL`을 전달하지만 로컬 Postgres 컨테이너는 기본 개발 의존성으로 같이 뜰 수 있습니다. 외부 DB만 확인할 때는 host-run `make local-up`이 더 단순합니다.
- 공유 DB에 seed가 필요 없으면 `SEED_ON_STARTUP=false`를 함께 설정합니다.

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
- `GET /v1/me/archive?month=YYYY-MM`
- `GET /v1/me/archive/{YYYY-MM-DD}`
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
- 기사 상세, feed, archive, scraps는 로그인된 현재 사용자 기준으로 동작합니다.
- `GET /v1/me/feed`는 Asia/Seoul 기준 오늘의 daily feed snapshot을 lazy 생성/조회한 뒤 viewed/check-in 처리하고, `snapshot_id`, `feed_date`, `status`, `read_count`, `total_count`, `mode`, `blocks`를 반환합니다. `blocks[].articles` 카드 shape는 기존 프론트 호환을 유지합니다.
- `GET /v1/me/archive?month=YYYY-MM`는 저장된 snapshot day metadata만 반환합니다. 월간 달력용 응답이며 `days[].items`는 포함하지 않습니다.
- `GET /v1/me/archive/{YYYY-MM-DD}`는 해당 날짜의 저장된 snapshot item을 snapshot sort order대로 반환하고, 열람 시 viewed/check-in 처리합니다.
- `GET /v1/articles/{article_id}`와 `GET /v1/me/articles/{article_id}`는 성공한 상세 열람을 read로 기록합니다. feed/archive에서 상세로 이동할 때 `?snapshot_id={snapshot_id}`를 넘기면 해당 snapshot의 `read_count`/`completed` 계산에 반영됩니다. snapshot 없이 열람하면 기사 단위 read만 저장됩니다.
- `status`는 snapshot 상태입니다. `generated`는 아직 확인 전, `viewed`는 feed/archive date를 열어본 상태, `completed`는 snapshot 내 모든 item을 읽은 상태입니다.
- `is_scrapped`는 현재 사용자의 스크랩 상태를 뜻하며 snapshot/read 상태와 독립적입니다.

온보딩 선호 규칙:
- wide: `primary_categories` 3~5개, `subcategories` 비어 있어야 함
- narrow: `primary_categories` 정확히 1개, `subcategories` 1개 이상
- 둘 다 중복 금지

## Snapshot feed/archive 응답 계약

### `GET /v1/me/feed`

홈 피드는 현재 preference로 매번 재계산하지 않고 daily feed snapshot을 기준으로 응답합니다. 오늘 snapshot이 없으면 API가 현재 사용자에 대해 lazy 생성하고, 응답 전 `first_viewed_at`을 최초 1회 기록합니다.

주요 필드:
- `user_id`: 현재 사용자 id
- `snapshot_id`: 오늘 daily feed snapshot id. article detail 이동 시 `snapshot_id` query로 전달합니다.
- `feed_date`: `YYYY-MM-DD`, Asia/Seoul 기준 오늘 날짜
- `status`: `generated` | `viewed` | `completed`
- `read_count`: 이 snapshot에서 read 처리된 article 수
- `total_count`: snapshot item 수
- `mode`: snapshot 생성 당시 preference mode
- `blocks[]`: snapshot item을 저장된 block/sort 순서대로 묶은 feed block
- `blocks[].articles[].is_scrapped`: 현재 사용자 기준 scrap 상태

### `GET /v1/me/archive?month=YYYY-MM`

월간 아카이브는 달력용 metadata만 내려줍니다. 해당 월에 저장된 snapshot 날짜만 `days[]`에 포함하며, 날짜별 기사 목록은 포함하지 않습니다.

`days[]` 필드:
- `date`: snapshot 날짜
- `snapshot_id`: daily feed snapshot id
- `status`: `generated` | `viewed` | `completed`
- `has_feed`: `total_count > 0`
- `count` / `total_count`: snapshot item 수. 현재는 같은 값입니다.
- `read_count`: 이 snapshot에서 read 처리된 article 수
- `first_viewed_at`: feed 또는 daily archive를 처음 연 시각. 없으면 미확인 상태입니다.
- `completed_at`: 모든 snapshot item을 읽어 completed가 된 시각

### `GET /v1/me/archive/{YYYY-MM-DD}`

날짜 상세 아카이브는 저장된 snapshot item을 현재 preference로 재계산하지 않고 그대로 반환합니다. endpoint를 열면 해당 snapshot이 viewed/check-in 처리됩니다.

주요 필드:
- `user_id`, `date`, `snapshot_id`, `status`, `read_count`, `total_count`
- `items[]`: snapshot 저장 순서의 article card 목록
- `items[].is_scrapped`: snapshot 생성 당시 값이 아니라 현재 사용자 기준 scrap 상태

### 상태 전이와 달력 매핑

| Backend 조건 | API status/field | 프론트 달력 의미 | 권장 표시 |
| --- | --- | --- | --- |
| `days[]`에 날짜 없음 | no snapshot | 피드 없음 | 흐리게/클릭 불가 |
| snapshot 존재, `first_viewed_at=null` | `status=generated`, `read_count=0` | 미확인 피드 있음 | 강조 점/새 피드 표시 |
| feed 또는 daily archive 열람 | `status=viewed`, `first_viewed_at!=null` | 확인/출첵 완료 | 체크 또는 확인 색상 |
| 일부 상세 열람 | `status=viewed`, `0 < read_count < total_count` | 일부 읽음 | `읽음 n/m` 또는 진행 표시 |
| 모든 snapshot item 상세 열람 | `status=completed`, `completed_at!=null` | 완료 | 완료 체크/완료 색상 |

read 처리 기준은 article detail endpoint 성공 응답입니다. detail 요청에 `snapshot_id`가 있으면 해당 snapshot 완료 계산에 반영되고, 없으면 snapshot 상태는 바꾸지 않습니다.

### Scheduler run report

기사 import 성공 후 scheduler wrapper는 onboarded 사용자별 오늘 snapshot을 생성하고, 최신 report와 archive report에 아래 필드를 기록합니다. import 실패 또는 이전 step 실패 시 snapshot generation은 실행하지 않습니다. 개별 사용자 실패는 전체 pipeline 실패로 만들지 않고 counter에만 반영합니다.

```json
{
  "feed_date": "2026-05-20",
  "snapshot_generation": {
    "attempted_user_count": 10,
    "generated_count": 9,
    "skipped_viewed_count": 1,
    "failed_count": 0
  }
}
```

- `attempted_user_count`: snapshot 생성 대상 onboarded user 수
- `generated_count`: 새로 생성했거나 미확인 snapshot을 재생성한 수
- `skipped_viewed_count`: 이미 확인한 snapshot이라 보존한 수
- `failed_count`: 사용자별 생성 중 예외가 난 수

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
