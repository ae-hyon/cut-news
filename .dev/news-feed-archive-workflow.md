# 나의 뉴스 피드 / 월간 아카이브 워크플로우

작성일: 2026-05-20

## 결론

제품 요구사항 기준으로 `나의 뉴스 아카이브`는 단순히 과거 기사를 현재 관심사로 다시 필터링하는 화면이 아니라, 사용자별로 매일 확정된 개인화 피드 스냅샷을 보관하고 그 날짜별 확인/읽음 상태를 보여주는 기능이어야 한다.

현재 backend 구현은 Phase 1~7 기준으로 이 목표를 만족하도록 전환됐다.

- 현재 있음: 매일 기사 수집/요약/import, 사용자별 daily feed snapshot 저장, 날짜별 viewed/check-in 상태, 기사 상세 기반 read tracking, 과거 피드 고정, scheduler import 이후 snapshot generation report
- frontend 구현은 별도 담당자가 이어갈 수 있도록 아래 API 계약과 달력 상태 매핑을 기준으로 한다.

## 현재 구현된 운영 파이프라인

루트 Docker Compose 기준으로 `news-scheduler` 컨테이너가 매일 `AI_NEWS_GENERATION_TIME`에 파이프라인을 실행한다. 기본값은 `08:30:00`, timezone 메타데이터는 `Asia/Seoul`이다.

현재 파이프라인 단계:

1. collect
   - crawler가 Naver 또는 seeded source에서 뉴스를 수집한다.
   - 결과는 crawler output에 저장된다.

2. export_raw
   - crawler 결과를 summarizer raw input으로 export한다.
   - 기존 raw/json/scored/summarized/verified derived output을 정리한다.

3. summarize
   - summarizer pipeline이 raw 기사를 구조화/점수화/요약/검증한다.

4. import
   - backend import script가 검증된 summarized articles를 backend DB의 `articles` 테이블에 upsert/import한다.

5. snapshot_generation
   - import가 성공하면 onboarded 사용자별 오늘 daily feed snapshot을 생성한다.
   - `NEWS_SCHEDULE_TIMEZONE` 기준 feed date를 쓰며 기본값은 `Asia/Seoul`이다.
   - 이미 viewed/check-in 된 snapshot은 보존하고 `skipped_viewed_count`로 센다.

6. run report
   - 최신 결과는 `apps/summarizer/data/run_report.json`에 저장된다.
   - 실행별 archive는 `apps/summarizer/data/run_reports/run_*.json`에 저장된다.
   - `feed_date`와 `snapshot_generation` counter가 포함된다.

## 현재 API 동작

### 홈 피드

`GET /v1/me/feed`는 현재 로그인 사용자의 Asia/Seoul 기준 오늘 daily feed snapshot을 반환한다. 오늘 snapshot이 없으면 lazy 생성하고, 응답 전 viewed/check-in 처리한다.

- `snapshot_id`, `feed_date`, `status`, `read_count`, `total_count`, `mode`, `blocks`를 반환한다.
- `blocks[].articles`는 기존 article card shape를 유지한다.
- `is_scrapped`는 snapshot 생성 당시 값이 아니라 현재 사용자의 스크랩 상태를 반영한다.
- snapshot 생성에는 현재 preference가 쓰이지만, 생성 후 저장된 snapshot item/block 순서가 조회 기준이 된다.

### 월간 아카이브

`GET /v1/me/archive?month=YYYY-MM`은 저장된 daily snapshot 기준으로 달력용 날짜 metadata만 반환한다. 현재 preference로 과거 기사를 재필터링하지 않는다.

- 응답: `{user_id, month, days}`
- `days[]`: `{date, snapshot_id, status, has_feed, count, total_count, read_count, first_viewed_at, completed_at}`
- 월간 응답에는 `items`가 없다. 날짜 클릭 후 daily archive endpoint로 item을 조회한다.

`GET /v1/me/archive/YYYY-MM-DD`는 해당 날짜의 저장된 snapshot item/read/scrap 상태를 반환하고, 열람 시 snapshot을 viewed/check-in 처리한다.

- 응답: `{user_id, date, snapshot_id, status, read_count, total_count, items}`
- `items[]`는 snapshot item의 `sort_order` 순서를 따른다.
- `items[].is_scrapped`는 현재 사용자 기준 scrap 상태이다.

기사 상세 endpoint는 성공한 열람을 read로 기록한다. feed/archive에서 상세로 이동할 때 `snapshot_id` query를 넘기면 해당 snapshot의 `read_count`와 `completed` 계산에 반영된다.

## 제품상 맞는 목표 워크플로우

### 매일 아침 생성 플로우

매일 아침 파이프라인은 기사 import 이후 사용자별 daily feed snapshot 생성 단계까지 수행해야 한다.

목표 단계:

1. 기사 수집
2. 요약/검증
3. articles import
4. active/onboarded 사용자 목록 조회
5. 각 사용자 preference 기준으로 오늘의 피드 후보 계산
6. 사용자별 daily feed snapshot 저장
7. snapshot에 포함된 기사 순서/block/category/생성 기준 preference를 고정
8. 이후 홈 피드와 아카이브는 해당 날짜 snapshot을 기준으로 조회

### Snapshot의 의미

Daily feed snapshot은 `그 날짜에 해당 사용자에게 제공된 뉴스 묶음`이다.

요구사항:

- 사용자별로 다르다.
- 날짜별로 고정된다.
- 이후 preference가 바뀌어도 과거 snapshot은 바뀌지 않는다.
- snapshot 생성 시점의 preference도 기록되어야 추적 가능하다.
- 재실행 시 같은 날짜/user에 대해 idempotent하게 갱신할지, 이미 확정된 snapshot은 유지할지 정책이 필요하다.

권장 정책:

- 아직 사용자에게 노출되지 않은 snapshot은 재생성 가능
- 사용자가 이미 확인한 snapshot은 기본적으로 고정
- 운영자 수동 repair 또는 force regenerate는 별도 audit log와 함께 허용

## 읽음/출첵 상태

월간 아카이브는 날짜별 상태를 표현해야 한다.

### 날짜 단위 상태

Backend 저장 status는 `generated`, `viewed`, `completed` 세 가지를 사용한다. frontend 달력은 아래 조건으로 product state를 표현한다.

| Backend 조건 | API status/field | 달력 의미 | 권장 표시 |
| --- | --- | --- | --- |
| `days[]`에 날짜 없음 | no snapshot | 피드 없음 | 흐리게/클릭 불가 |
| snapshot 존재, `first_viewed_at=null` | `generated` | 피드는 생성됐지만 아직 열어보지 않음 | 강조 점/새 피드 |
| feed 또는 daily archive 열람 | `viewed`, `first_viewed_at!=null` | 확인/출첵 완료 | 체크/확인 색상 |
| 일부 상세 열람 | `viewed`, `0 < read_count < total_count` | 일부 읽음 | `읽음 n/m`/진행 표시 |
| 전체 상세 열람 | `completed`, `completed_at!=null` | 완료 | 완료 체크/완료 색상 |

### 기사 단위 상태

- unread: 아직 상세를 열지 않음
- opened: 상세를 열어봄
- read: 읽음으로 인정됨
- scrapped: 스크랩됨. 읽음과 별개 상태

읽음 인정 기준은 제품 정책으로 정해야 한다.

가능한 기준:

- 상세 페이지 진입 즉시 read 처리
- 상세 페이지 N초 이상 체류 시 read 처리
- 원문 링크 클릭 시 read 처리
- 사용자가 명시적으로 읽음 처리

MVP는 상세 페이지 진입 즉시 `opened/read` 처리하는 방식이 단순하다. 이후 체류 시간 기반으로 고도화할 수 있다.

## 화면 요구사항

### 월간 달력

각 날짜는 다음 상태를 시각적으로 구분해야 한다.

- 미래 날짜: 비활성
- 피드 없음: 흐리게 표시, 클릭 불가
- 피드 있음 + 미확인: 강조 점 또는 알림 표시
- 확인함: 다른 색 점 또는 체크 표시
- 일부 읽음: `읽음 n/m` 또는 진행 링
- 완료: 체크/완료 색상

### 날짜 상세

날짜 클릭 시 그 날짜의 저장된 snapshot을 보여준다.

표시 요소:

- 날짜
- 총 기사 수
- 읽은 기사 수 / 전체 기사 수
- 기사 카드 목록
- 각 카드의 읽음/안읽음 상태
- 각 카드의 스크랩 상태
- 기사 상세 이동

## 필요한 데이터 모델 초안

### daily_feed_snapshots

- id
- user_id
- feed_date (`YYYY-MM-DD`)
- status (`generated`, `viewed`, `completed` 등)
- generated_at
- first_viewed_at
- completed_at nullable
- preference_mode_at_generation
- primary_categories_json_at_generation
- subcategories_json_at_generation
- generation_source/run_id
- unique(user_id, feed_date)

### daily_feed_snapshot_items

- id
- snapshot_id
- article_id
- block_key
- block_title
- sort_order
- score_weight_at_generation
- created_at
- unique(snapshot_id, article_id)

### user_article_reads

- id
- user_id
- article_id
- snapshot_id nullable
- opened_at
- read_at nullable
- read_duration_seconds nullable
- read_source (`home`, `archive`, `detail`, `external` 등)
- unique(user_id, article_id, snapshot_id) 또는 event log 방식 선택

## API 계약 방향

### Home feed

`GET /v1/me/feed`

- 오늘 날짜의 snapshot이 있으면 snapshot을 반환한다.
- snapshot이 없으면 정책에 따라 즉시 생성하거나 빈 상태/준비중을 반환한다.
- 응답에는 snapshot id/date/status/read progress가 포함되어야 한다.

### Monthly archive

`GET /v1/me/archive?month=YYYY-MM`

- 저장된 daily snapshot 기준으로 날짜별 상태를 반환한다.
- 날짜별 기사 전체를 내려줄 수도 있지만, MVP 이후에는 달력용 요약만 내려주고 날짜 클릭 시 상세 조회하는 편이 낫다.

예시 필드:

- date
- status
- total_count
- read_count
- has_feed
- first_viewed_at
- completed_at

### Daily archive

`GET /v1/me/archive/YYYY-MM-DD`

- 해당 날짜의 저장된 snapshot과 item/read/scrap 상태를 반환한다.
- 현재 preference로 재계산하면 안 된다.

### Read tracking

별도 read mutation route 대신 article detail GET 성공 시 read를 기록한다.

- `GET /v1/articles/{article_id}?snapshot_id={snapshot_id}`
- `GET /v1/me/articles/{article_id}?snapshot_id={snapshot_id}`

`snapshot_id`가 있으면 해당 snapshot의 read/completion 상태에 반영한다. `snapshot_id` 없이 열람하면 article-only read로 저장하고 snapshot 상태는 바꾸지 않는다. 같은 user/article/snapshot 조합의 중복 열람은 idempotent하다.

## Scheduler run report 계약

기사 import가 성공한 실행은 최신 report와 archive report에 snapshot generation 결과를 추가한다. import 실패 또는 이전 단계 실패 시 snapshot generation은 실행하지 않는다. 개별 사용자 생성 실패는 전체 pipeline 실패로 만들지 않고 `failed_count`로만 기록한다.

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

- `feed_date`: scheduler timezone 기준 snapshot date
- `attempted_user_count`: onboarded snapshot 대상 user 수
- `generated_count`: 새 snapshot 생성 또는 미확인 snapshot 재생성 수
- `skipped_viewed_count`: 이미 viewed/completed라 보존한 snapshot 수
- `failed_count`: 사용자별 생성 예외 수

## 결정해야 할 제품 정책

1. Snapshot 생성 대상 사용자
   - onboarded 사용자 전체인가?
   - 최근 N일 내 접속 사용자만인가?
   - 비활성 사용자도 계속 생성하는가?

2. Snapshot 생성 시점
   - 아침 pipeline 이후 모든 사용자에 대해 즉시 생성
   - 사용자가 처음 접속할 때 lazy 생성
   - 혼합: active users는 precompute, 나머지는 lazy

3. Snapshot 재생성 정책
   - 같은 날짜에 pipeline rerun 시 덮어쓰기 여부
   - 이미 확인한 피드 고정 여부

4. 읽음 인정 기준
   - 상세 진입 즉시
   - 체류 시간
   - 원문 클릭

5. 출첵 기준
   - 홈 피드 진입
   - 날짜 아카이브 열람
   - 기사 1개 이상 읽음

## 다음 구현 순서 제안

1. workflow 문서/요구사항 확정
2. DB migration: daily feed snapshot, snapshot items, read tracking 추가
3. FeedService를 runtime 계산에서 snapshot 생성/조회 구조로 분리
4. scheduler pipeline import 이후 snapshot generation step 추가
5. `/v1/me/feed`, `/v1/me/archive` 응답 계약 확장
6. frontend 달력 상태 표시와 read tracking 연동
7. tests: snapshot 고정, preference 변경 후 과거 archive 불변, read/check-in 상태 반영
