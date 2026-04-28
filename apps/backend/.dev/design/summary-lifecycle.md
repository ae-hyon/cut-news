# Summary Lifecycle

최종 갱신: 2026-04-28 02:13:14 KST

## 목적
홈/상세/스크랩/아카이브에서 summary 데이터가 어디서 오고, 언제 새 요약을 생성하는지 백엔드 관점에서 명확히 정리한다.

## 현재 결정
- 앱의 홈/상세/스크랩/아카이브는 현재 DB seed에 저장된 기사 summary를 읽는다.
- `POST /v1/summaries`는 사용자 앱이 모든 화면 진입 때마다 직접 호출하는 runtime endpoint가 아니다.
- 현재 `/v1/summaries`는 백엔드 개발/운영/사전 적재(ingest) 경계 검증용 endpoint로 둔다.
- 즉, 현재 제품 플로우에서 summary 생성과 summary 조회는 분리되어 있다.

## 화면별 데이터 출처

### 1. 홈 피드
사용 API:
- `GET /v1/users/{user_id}/feed`

현재 summary 출처:
- `articles.summary`
- 이미 저장된 카드용 요약 문자열

현재 홈이 요구하는 필드:
- article id
- title
- summary
- primary_category
- subcategory
- published_at
- original_url
- is_scrapped

새 요약 생성 여부:
- 아니오
- 홈 조회 시 `POST /v1/summaries`를 호출하지 않음

### 2. 기사 상세
사용 API:
- `GET /v1/articles/{article_id}`

현재 상세의 데이터 출처:
- `title`: 저장된 기사 엔티티
- `summary`: 저장된 기사 엔티티
- `content`: 저장된 기사 엔티티
- `original_url`: 저장된 기사 엔티티

새 요약 생성 여부:
- 아니오
- 상세 조회 시에도 기존 summary를 그대로 사용

### 3. 스크랩
사용 API:
- `GET /v1/users/{user_id}/scraps`
- `PUT /v1/users/{user_id}/scraps/{article_id}`
- `DELETE /v1/users/{user_id}/scraps/{article_id}`

현재 summary 출처:
- 스크랩 목록도 기사 엔티티의 기존 summary 재사용

새 요약 생성 여부:
- 아니오

### 4. 아카이브
사용 API:
- `GET /v1/users/{user_id}/archives?month=YYYY-MM`
- `GET /v1/users/{user_id}/archives/{archive_date}`

현재 summary 출처:
- 기사 엔티티의 기존 summary 재사용

새 요약 생성 여부:
- 아니오

## `/v1/summaries`의 현재 역할
현재 역할:
- `../news_summurizer` import 경계를 FastAPI에서 노출
- 요약 요청 payload를 typed boundary로 변환
- summarizer 결과를 API response schema로 재검증
- 길이 계약 위반 등 contract violation을 502로 표준화

현재 비역할:
- 홈 피드 실시간 렌더링 중 즉석 요약 생성
- 상세 진입 때마다 즉시 재요약
- 스크랩/아카이브 조회 중 배치 생성

## 추천 운영 흐름
1. 별도 ingest/admin flow가 기사 원문을 확보
2. 필요 시 `POST /v1/summaries` 또는 내부 adapter 호출로 요약 생성
3. 검증된 summary를 article 저장소에 적재
4. 사용자 화면 API는 저장된 summary만 읽음

## 왜 이렇게 두는가
- 홈/상세/스크랩/아카이브 응답 시간을 외부 LLM 호출에 묶지 않기 위해서다.
- summary 생성 실패와 앱 조회 실패를 분리할 수 있다.
- core-backend는 사용자-facing resource API이고, summarizer는 생성 파이프라인/도구 성격이 더 강하다.

## 향후 확장 포인트
추후 필요하면 다음 중 하나로 확장 가능:
- A. ingest/backoffice 전용 내부 서비스로 유지
- B. 관리자/운영용 protected endpoint로 유지
- C. 일부 상세 화면에서 on-demand regenerate endpoint 추가

현재 단계에서는 A/B가 더 적합하다.
