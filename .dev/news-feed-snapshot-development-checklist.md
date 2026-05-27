# 나의 뉴스 피드 Snapshot 개발 체크리스트

작성일: 2026-05-20
상태: 개발 전 계획 확정용
관련 문서: `.dev/news-feed-archive-workflow.md`

## 목표

현재 runtime preference 기반으로 재계산되는 홈 피드/월간 아카이브를 사용자별 daily feed snapshot 기반으로 전환한다.

최종 목표는 다음 불변식을 만족하는 것이다.

- 매일 아침 기사 import 이후 사용자별 오늘의 피드가 저장된다.
- 저장된 snapshot은 해당 날짜에 사용자에게 제공된 뉴스 묶음이다.
- 과거 snapshot은 이후 preference 변경에 영향을 받지 않는다.
- 월간 아카이브는 저장된 snapshot의 날짜별 상태를 보여준다.
- 날짜별 확인/출첵 상태와 기사별 읽음 상태를 추적한다.
- 기존 스크랩 상태는 snapshot/read 상태와 독립적으로 유지한다.

## 개발 원칙

- Backend 먼저 진행한다. Frontend는 명시 요청 전까지 수정하지 않는다.
- 각 단계는 테스트 먼저 작성하고 구현한다.
- API 계약이 바뀌면 schema, route test, OpenAPI contract test, README/API 문서를 함께 갱신한다.
- 기존 runtime 계산 로직은 바로 삭제하지 말고 snapshot 생성 로직에서 재사용 가능한 selector로 분리한다.
- scheduler 자동 생성은 DB/API 기반 snapshot 기능이 안정화된 뒤 마지막에 연결한다.
- 운영 데이터 보호를 위해 이미 확인한 snapshot 재생성 정책은 명시적으로 구현한다.

## 현재 기준선

현재 구현 파일:

- Feed 계산: `apps/backend/app/application/services/feed_service.py`
- Article/UserPreference/Scrap repo protocol: `apps/backend/app/domain/repositories.py`
- SQLAlchemy models: `apps/backend/app/infrastructure/models.py`
- SQLAlchemy repo 구현: `apps/backend/app/infrastructure/repositories.py`
- API schemas: `apps/backend/app/presentation/schemas.py`
- User routes: `apps/backend/app/presentation/api/routes/users.py`
- DI: `apps/backend/app/presentation/api/dependencies.py`
- Pipeline wrapper: `apps/backend/app/scripts/run_news_pipeline_job.py`
- Feed tests: `apps/backend/tests/test_feed_service.py`
- User route tests: `apps/backend/tests/test_user_routes.py`
- OpenAPI contract tests: `apps/backend/tests/test_openapi_frontend_contract.py`
- Pipeline tests: `apps/backend/tests/test_run_news_pipeline_job.py`

현재 한계:

- `GET /v1/me/feed`는 `articles`와 현재 preference로 즉시 계산한다.
- `GET /v1/me/archive?month=YYYY-MM`는 월별 articles를 현재 preference로 필터링한다.
- 사용자별 daily snapshot table이 없다.
- snapshot item table이 없다.
- read/check-in table이 없다.
- scheduler import 이후 사용자별 snapshot 생성 단계가 없다.

## Phase 0: 정책 확정 체크리스트

개발 전에 아래 정책을 문서에서 확정한다.

- [ ] Snapshot 생성 대상
  - MVP 기본값: `onboarding_completed=true`인 user_preferences 전체
  - 추후 active user 제한은 별도 최적화
- [ ] Snapshot 생성 시점
  - MVP 기본값: scheduler import 이후 batch 생성
  - snapshot이 없을 때 `GET /v1/me/feed`에서 lazy 생성 허용 여부는 별도 결정
- [ ] Snapshot 재생성 정책
  - MVP 기본값: `first_viewed_at is null`이면 같은 user/date snapshot 재생성 가능
  - `first_viewed_at is not null`이면 기본적으로 고정
- [ ] 출첵/view 기준
  - MVP 기본값: 오늘 feed 또는 archive date endpoint를 열면 snapshot viewed 처리
- [ ] read 기준
  - MVP 기본값: article detail endpoint 진입 시 opened/read 처리
- [ ] completed 기준
  - MVP 기본값: snapshot item 전체 read 시 completed
- [ ] Timezone 기준
  - MVP 기본값: scheduler와 동일하게 Asia/Seoul feed_date 사용

## Phase 1: 데이터 모델과 repository 기반 만들기

상태: 완료됨 (2026-05-20)

완료 파일:

- `apps/backend/app/domain/entities.py`
- `apps/backend/app/domain/repositories.py`
- `apps/backend/app/infrastructure/models.py`
- `apps/backend/app/infrastructure/repositories.py`
- `apps/backend/alembic/versions/0006_daily_feed_snapshots.py`
- `apps/backend/tests/test_daily_feed_snapshot_repository.py`

검증:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_daily_feed_snapshot_repository.py -q
PYTHONPATH=. uv run pytest tests/test_daily_feed_snapshot_repository.py tests/test_user_preference_repository.py tests/test_feed_service.py -q
DATABASE_URL="sqlite+pysqlite:////tmp/cut-news-alembic-smoke.db" uv run alembic -c alembic.ini upgrade head
PYTHONPATH=. uv run pytest tests/ -q
```

결과: `99 passed`

목표: DB에 snapshot/read 상태를 저장하고 조회할 수 있는 최소 기반을 만든다.

### 1.1 Domain entity 추가

파일:

- Modify: `apps/backend/app/domain/entities.py`

추가 후보:

- `DailyFeedSnapshot`
- `DailyFeedSnapshotItem`
- `UserArticleRead`

필드 초안:

```python
class DailyFeedSnapshot(DomainModel):
    id: int | None = None
    user_id: str
    feed_date: str
    status: str
    generated_at: datetime
    first_viewed_at: datetime | None = None
    completed_at: datetime | None = None
    preference_mode: PreferenceMode
    primary_categories: list[str]
    subcategories: list[str]
    generation_source: str | None = None
    items: list[DailyFeedSnapshotItem] = Field(default_factory=list)
```

체크리스트:

- [ ] entity test 또는 repository test에서 사용할 수 있게 Pydantic 모델 추가
- [ ] status 문자열은 우선 `generated`, `viewed`, `completed`로 제한할지 enum으로 뺄지 결정
- [ ] preference-at-generation 필드는 JSON 문자열이 아니라 domain에서는 list로 다룬다

### 1.2 SQLAlchemy model 추가

파일:

- Modify: `apps/backend/app/infrastructure/models.py`

테이블:

- `daily_feed_snapshots`
- `daily_feed_snapshot_items`
- `user_article_reads`

필수 제약:

- `daily_feed_snapshots`: unique `(user_id, feed_date)`
- `daily_feed_snapshot_items`: unique `(snapshot_id, article_id)`
- `user_article_reads`: MVP는 unique `(user_id, article_id, snapshot_id)` 권장

체크리스트:

- [ ] article FK는 `articles.id` ondelete cascade
- [ ] user FK는 현재 user source가 `user_preferences.user_id`이므로 동일하게 연결
- [ ] JSON list 저장은 `Text` + `json.dumps/loads`로 기존 코드 스타일에 맞춘다
- [ ] SQLite test DB와 Postgres 모두 동작하는 SQLAlchemy 타입만 사용한다

### 1.3 Repository protocol 추가

파일:

- Modify: `apps/backend/app/domain/repositories.py`

추가 protocol 후보:

- `DailyFeedSnapshotRepository`
- `UserArticleReadRepository`

필요 메서드:

```python
def get_by_user_date(self, user_id: str, feed_date: str) -> DailyFeedSnapshot | None: ...
def list_by_user_month(self, user_id: str, month: str) -> list[DailyFeedSnapshot]: ...
def save(self, snapshot: DailyFeedSnapshot) -> DailyFeedSnapshot: ...
def replace_items(self, snapshot_id: int, items: list[DailyFeedSnapshotItem]) -> None: ...
def mark_viewed(self, snapshot_id: int, viewed_at: datetime) -> DailyFeedSnapshot: ...
```

Read repo:

```python
def mark_read(self, user_id: str, article_id: str, snapshot_id: int | None, read_at: datetime) -> None: ...
def list_read_article_ids(self, user_id: str, snapshot_id: int) -> set[str]: ...
```

체크리스트:

- [ ] Protocol에 구현에서 필요한 최소 메서드만 먼저 넣는다
- [ ] read 이벤트 log가 아니라 latest-state table로 MVP를 시작한다

### 1.4 SQLAlchemy repository 구현과 테스트

파일:

- Modify: `apps/backend/app/infrastructure/repositories.py`
- Create/Modify: `apps/backend/tests/test_daily_feed_snapshot_repository.py`

테스트 우선 작성:

- [ ] user/date로 snapshot 저장 후 조회 가능
- [ ] item 순서가 `sort_order`로 보존됨
- [ ] month 조회가 `YYYY-MM-%` feed_date 기준으로 동작
- [ ] 같은 user/date 저장 시 idempotent update 또는 명시적 conflict 정책이 동작
- [ ] viewed 표시 시 `first_viewed_at`이 최초 한 번만 기록됨
- [ ] read 표시 후 snapshot read ids 조회 가능

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_daily_feed_snapshot_repository.py -q
```

## Phase 2: Feed selection 로직을 snapshot 생성에 재사용 가능하게 분리

상태: 완료됨 (2026-05-20)

완료 파일:

- `apps/backend/app/application/services/feed_service.py`
- `apps/backend/tests/test_feed_service.py`

검증:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_feed_service.py -q
PYTHONPATH=. uv run pytest tests/test_feed_service.py tests/test_daily_feed_snapshot_repository.py tests/test_user_preference_repository.py -q
PYTHONPATH=. uv run pytest tests/ -q
```

결과: `101 passed`

목표: 기존 `FeedService.get_feed()`가 가진 선택/정렬/중복제거 로직을 snapshot 생성에서도 같은 방식으로 쓴다.

파일:

- Modify: `apps/backend/app/application/services/feed_service.py`
- Modify: `apps/backend/tests/test_feed_service.py`

작업:

- [ ] 현재 `get_feed()`의 block 계산을 private method로 분리
  - 예: `_build_feed_blocks_for_preference(...)`
- [ ] 반환 block이 article 객체와 block key/title/weight/order 정보를 포함하게 정리
- [ ] wide/narrow 기존 테스트가 모두 그대로 통과해야 함
- [ ] low score 제외, duplicate 제거, fallback 동작 테스트 유지

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_feed_service.py -q
```

## Phase 3: Snapshot generation service 추가

상태: 완료됨 (2026-05-20)

완료 파일:

- `apps/backend/app/application/services/daily_feed_snapshot_service.py`
- `apps/backend/app/presentation/api/dependencies.py`
- `apps/backend/tests/test_daily_feed_snapshot_service.py`

검증:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_daily_feed_snapshot_service.py tests/test_daily_feed_snapshot_repository.py tests/test_feed_service.py -q
PYTHONPATH=. uv run pytest tests/ -q
```

결과: `105 passed`

목표: 특정 user/date에 대해 preference-at-generation을 고정한 snapshot을 만든다.

파일:

- Modify: `apps/backend/app/application/services/feed_service.py` 또는 Create: `apps/backend/app/application/services/daily_feed_snapshot_service.py`
- Modify: `apps/backend/app/presentation/api/dependencies.py`
- Create: `apps/backend/tests/test_daily_feed_snapshot_service.py`

권장 구조:

- `FeedService`: article 선택/기존 feed API helper 유지
- `DailyFeedSnapshotService`: snapshot 생성/조회/view/read 상태 orchestration

핵심 메서드:

```python
def generate_for_user_date(
    self,
    user_id: str,
    feed_date: str,
    generation_source: str | None = None,
    force: bool = False,
) -> DailyFeedSnapshot: ...
```

정책:

- [ ] 기존 snapshot이 없으면 생성
- [ ] 기존 snapshot이 있고 `first_viewed_at is null`이면 재생성 가능
- [ ] 기존 snapshot이 있고 viewed 상태이면 `force=False`에서 기존 snapshot 반환
- [ ] `force=True` 정책은 MVP에서 구현하지 않거나, 구현 시 테스트와 audit source 필수

테스트:

- [ ] snapshot 생성 시 현재 preference mode/categories/subcategories가 저장됨
- [ ] preference 변경 후에도 기존 snapshot item은 바뀌지 않음
- [ ] viewed snapshot은 일반 재생성에서 유지됨
- [ ] unviewed snapshot은 재생성 가능
- [ ] item에 block_key, block_title, sort_order, article_id가 저장됨

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_daily_feed_snapshot_service.py -q
```

## Phase 4: Home feed API를 snapshot 기반으로 전환

상태: 완료됨 (2026-05-20)

완료 파일:

- `apps/backend/app/presentation/schemas.py`
- `apps/backend/app/presentation/api/routes/users.py`
- `apps/backend/app/application/services/daily_feed_snapshot_service.py`
- `apps/backend/tests/test_feed_routes.py`
- `apps/backend/tests/test_openapi_frontend_contract.py`
- `apps/backend/README.md`

검증:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_feed_routes.py tests/test_openapi_frontend_contract.py tests/test_daily_feed_snapshot_service.py -q
PYTHONPATH=. uv run pytest tests/ -q
python -m compileall app tests/test_feed_routes.py tests/test_openapi_frontend_contract.py
```

결과: `105 passed`

목표: `GET /v1/me/feed`가 오늘 snapshot을 반환하게 한다.

파일:

- Modify: `apps/backend/app/presentation/schemas.py`
- Modify: `apps/backend/app/presentation/api/routes/users.py`
- Modify: `apps/backend/app/presentation/api/dependencies.py`
- Modify: `apps/backend/tests/test_feed_routes.py`
- Modify: `apps/backend/tests/test_openapi_frontend_contract.py`

응답 확장 후보:

```json
{
  "user_id": "demo-user",
  "snapshot_id": 1,
  "feed_date": "2026-05-20",
  "status": "generated",
  "read_count": 0,
  "total_count": 8,
  "mode": "wide",
  "blocks": []
}
```

MVP 정책:

- [x] 오늘 snapshot이 있으면 반환
- [x] 오늘 snapshot이 없으면 API 호출 시 lazy 생성할지, 빈 준비중 응답을 줄지 결정
- [x] 기존 frontend 호환을 위해 `mode`, `blocks[].articles` shape는 최대한 유지
- [x] 추가 필드는 optional이 아니라 명시 schema로 추가

테스트:

- [x] authenticated user만 접근 가능
- [x] snapshot metadata가 응답됨
- [x] block/article 순서가 snapshot item 순서 기준임
- [x] `is_scrapped`는 현재 scrap repo 기준으로 계산됨

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_feed_routes.py tests/test_openapi_frontend_contract.py -q
```

## Phase 5: Archive API를 snapshot 기반으로 전환

목표: 월간/일간 archive가 current preference 재계산을 중단하고 저장된 snapshot 기준으로 동작한다.

파일:

- Modify: `apps/backend/app/application/services/feed_service.py` 또는 snapshot service
- Modify: `apps/backend/app/presentation/schemas.py`
- Modify: `apps/backend/app/presentation/api/routes/users.py`
- Modify: `apps/backend/tests/test_user_routes.py`
- Modify: `apps/backend/tests/test_openapi_frontend_contract.py`

Monthly response 방향:

```json
{
  "user_id": "demo-user",
  "month": "2026-05",
  "days": [
    {
      "date": "2026-05-20",
      "snapshot_id": 1,
      "status": "viewed",
      "has_feed": true,
      "count": 8,
      "total_count": 8,
      "read_count": 3,
      "first_viewed_at": "2026-05-20T09:10:00+09:00",
      "completed_at": null
    }
  ]
}
```

Daily response 방향:

```json
{
  "user_id": "demo-user",
  "date": "2026-05-20",
  "snapshot_id": 1,
  "status": "viewed",
  "read_count": 3,
  "total_count": 8,
  "items": []
}
```

테스트:

- [x] 월간 archive는 snapshot이 있는 날짜만 반환
- [x] preference 변경 후 월간 archive 결과가 변하지 않음
- [x] 날짜 상세는 snapshot item 기준으로 article 반환
- [x] 날짜 상세 조회 시 viewed/check-in 처리됨
- [x] read_count/status가 read table 기준으로 계산됨
- [x] `is_scrapped`는 현재 scrap 상태로 계산됨

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_user_routes.py tests/test_openapi_frontend_contract.py -q
```

## Phase 6: Read tracking endpoint/동작 추가

목표: 기사 상세 진입을 read 처리로 연결한다.

파일:

- Modify: `apps/backend/app/presentation/api/routes/articles.py`
- Modify: `apps/backend/app/application/services/feed_service.py` 또는 snapshot service
- Modify: `apps/backend/tests/test_article_routes.py`
- Modify: `apps/backend/tests/test_user_routes.py`

MVP 정책:

- [x] article detail endpoint가 authenticated current user context를 이미 요구하므로 여기에서 `mark_read` 호출
- [x] snapshot context 없이 article만 읽은 경우를 허용할지 결정
- [x] archive/detail에서 snapshot id를 query로 넘기는 추가 계약이 필요한지 결정
- [x] 같은 article 중복 read는 idempotent

테스트:

- [x] article detail 진입 시 read 저장
- [x] 같은 article 재진입은 중복 row를 만들지 않음
- [x] snapshot item 전체 read 후 snapshot status가 completed로 바뀜
- [x] scrap 상태와 read 상태가 서로 덮어쓰지 않음

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_article_routes.py tests/test_user_routes.py -q
```

## Phase 7: Scheduler pipeline에 snapshot generation 연결

목표: import 성공 후 active/onboarded user 전체에 오늘 snapshot을 생성한다.

파일:

- Modify: `apps/backend/app/scripts/run_news_pipeline_job.py`
- Modify: `apps/backend/app/infrastructure/repositories.py`
- Modify: `apps/backend/app/domain/repositories.py`
- Modify: `apps/backend/tests/test_run_news_pipeline_job.py`

필요 repository:

- onboarding 완료 user id list 조회
  - 후보: `UserPreferenceRepository.list_onboarded_user_ids()`

Pipeline 위치:

1. collect
2. export_raw
3. summarize
4. import
5. generate_daily_snapshots
6. write run_report

Run report 추가 필드 후보:

```json
{
  "snapshot_generation": {
    "attempted_user_count": 10,
    "generated_count": 9,
    "skipped_viewed_count": 1,
    "failed_count": 0
  }
}
```

테스트:

- [x] import 성공 후 snapshot generation step이 호출됨
- [x] import 실패 시 snapshot generation은 호출되지 않음
- [x] run_report에 snapshot generation 결과가 포함됨
- [x] 개별 사용자 실패 정책: 전체 pipeline 실패 vs 사용자별 failed_count 기록을 결정하고 테스트

검증 명령:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/test_run_news_pipeline_job.py -q
```

## Phase 8: 문서/API 계약 갱신

상태: 완료됨 (2026-05-20)

완료 파일:

- `apps/backend/README.md`
- `.dev/news-feed-archive-workflow.md`
- `apps/backend/app/presentation/schemas.py`
- `apps/backend/tests/test_openapi_frontend_contract.py`

목표: frontend 개발자가 snapshot 기반 계약으로 구현할 수 있게 문서화한다.

파일 후보:

- Modify: backend README/API docs 위치 확인 후 갱신
- Modify: `.dev/news-feed-archive-workflow.md`
- Modify: `.dev/NEXT_SESSION.md`

체크리스트:

- [x] `/v1/me/feed` 응답 필드 문서화
- [x] `/v1/me/archive?month=YYYY-MM` 응답 필드 문서화
- [x] `/v1/me/archive/YYYY-MM-DD` 응답 필드 문서화
- [x] viewed/read/completed 상태 전이 문서화
- [x] scheduler run_report snapshot_generation 필드 문서화
- [x] frontend가 필요한 달력 상태 매핑 표 추가

## Phase 9: 전체 검증

상태: 완료됨 (2026-05-20)

검증 결과:

- `make test`: `114 passed`
- root compose API rebuild: `docker compose up -d --build api` 성공
- compose 상태: `api`/`db` healthy
- health smoke: `curl -sf http://127.0.0.1:8030/health` 성공
- categories smoke: `curl -sf http://127.0.0.1:8030/v1/categories` 성공, 10개 category 확인
- DB migration smoke: `alembic_version=0006_daily_feed_snapshots`, snapshot/read 테이블 3개 확인

참고: backend-only compose(`apps/backend/docker-compose.yml`)는 root full compose가 같은 `annoyingcap-*` container names를 이미 사용 중이면 name conflict가 난다. 이 경우 root compose stack 상태를 확인하거나 root compose의 `api` service를 rebuild/recreate해서 검증한다.

최소 backend 검증:

```bash
cd /Users/reddit/Project/cut-news/apps/backend
PYTHONPATH=. uv run pytest tests/ -q
```

Compose/E2E 검증은 DB/API 변경이 끝난 뒤 진행:

```bash
cd /Users/reddit/Project/cut-news
make backend-up
curl -sf http://127.0.0.1:8030/health
```

운영 smoke는 Naver credentials가 필요하므로 별도 승인/환경 확인 후 진행한다.

## 완료 기준

- [x] DB에 daily snapshot/read 상태가 저장된다.
- [x] 오늘 feed API가 snapshot 기반으로 응답한다.
- [x] 월간 archive API가 snapshot day summary를 응답한다.
- [x] 날짜 archive API가 저장된 snapshot item을 응답한다.
- [x] preference 변경 후 과거 archive가 변하지 않는 테스트가 있다.
- [x] read/check-in 상태가 응답에 반영되는 테스트가 있다.
- [x] scheduler import 이후 snapshot generation이 실행된다.
- [x] run_report에서 snapshot generation 결과를 확인할 수 있다.
- [x] OpenAPI contract test가 새 응답 계약을 검증한다.
- [x] backend 전체 테스트가 통과한다.

## 다음 작업 시작 순서

Snapshot backend migration Phase 1~9는 완료됐다. 다음 세션에서는 아래 순서로 정리/인계한다.

1. working tree의 generated summarizer data 삭제/생성분을 commit 대상에서 제외할지 정리한다.
2. backend 변경 파일과 `.dev/*` 문서만 선별해 최종 diff를 검토한다.
3. 필요하면 root compose 전체 stack smoke 또는 credential-gated Naver pipeline smoke를 별도 승인 후 진행한다.
4. frontend 담당자에게 Phase 8 README 계약과 달력 상태 매핑을 전달한다.
