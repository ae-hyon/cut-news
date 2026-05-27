# Annoying Cap Core Backend PRD

최종 갱신: 2026-04-28 14:20:07 KST

## 1. 문서 목적
이 문서는 `../어노잉캡-Flow.pdf`와 현재 구현 상태를 기준으로 Annoying Cap 메인 백엔드의 요구사항, 범위, 아키텍처, API 책임, 완료/미완료 항목을 관리하기 위한 제품 요구사항 문서다.

이 저장소는 다음 역할을 담당한다.
- 사용자 온보딩/선호 저장
- 카테고리/서브카테고리 제공
- 홈 피드/블록 조립
- 기사 상세/스크랩/아카이브 제공
- `../news_summurizer`를 import 해서 요약 기능 제공

이 저장소가 하지 않는 일:
- 요약 로직 자체를 여기서 다시 구현하지 않음
- 외부 인증 공급자 전체 구현 완료 상태를 가정하지 않음
- 운영 배포/실서비스 인증/권한 체계를 아직 완료된 것으로 간주하지 않음

## 2. 소스 오브 트루스
- 제품 플로우: `../어노잉캡-Flow.pdf`
- 요약 라이브러리: `../news_summurizer`
- 현재 구현 설명: `README.md`

## 3. PDF에서 정리한 핵심 요구사항
### 3.1 온보딩
1. 사용자는 초기에 `넓게 볼랭(Wide)` 또는 `깊게 볼랭(Narrow)` 모드를 선택한다.
2. Wide 유저:
   - 대분류를 최소 3개 이상 선택
   - 최대 5개까지 선택
   - 5개 초과 시 선택 불가/토스트 노출
3. Narrow 유저:
   - 대분류 1개 선택
   - 해당 대분류 아래 중카테고리 여러 개 선택
   - 수정 시 각 단계로 다시 이동 가능
4. 온보딩 완료 후 로그인 유도 및 홈으로 진입한다.
5. backend validation 규칙: wide는 대분류 3~5개/중복 금지/subcategory 금지, narrow는 대분류 1개 + subcategory 1개 이상/중복 금지.

### 3.2 홈/피드
1. 홈은 사용자가 선택한 관심사에 맞는 뉴스 블록을 보여준다.
2. PDF 상 메모에 따라 AI가 블록 가중치를 설정하고 블록 비중을 정한다.
3. 카드/블록형 배열 구조를 사용한다.
4. 기사 요약은 홈과 상세 진입 전반에서 일관된 길이 계약을 유지해야 한다.
5. 현재 backend 기본 정책: wide는 선택 순서대로 블록을 만들고 weight를 점감 적용, narrow는 단일 focus block으로 집중 노출한다.

### 3.3 기사 상세
1. 기사 제목, 날짜, 본문 요약/내용을 보여준다.
2. 원문 링크로 이동할 수 있어야 한다.
3. 상세에서 스크랩 토글이 가능해야 한다.

### 3.4 스크랩
1. 스크랩한 기사를 별도 화면에서 다시 볼 수 있어야 한다.
2. 스크랩 화면도 블록/리스트 형태로 재조합 가능해야 한다.

### 3.5 아카이브
1. 월간 캘린더/이력 구조를 제공한다.
2. 특정 날짜를 누르면 그 날짜의 뉴스 목록을 볼 수 있어야 한다.
3. 하루 단위로 다시 볼 수 있는 구조여야 한다.

## 4. 현재 제품/백엔드 범위
### 포함
- FastAPI 기반 REST API
- DDD + layered architecture
- local Postgres + Docker Compose
- Alembic migration
- seed 데이터 기반 로컬 검증 환경
- `news_summurizer` 연동 `/v1/summaries`
- 사용자 선호, 피드, 기사, 스크랩, 아카이브 API
- Kakao OAuth start/callback/session contract
- `provider_subject -> internal user_id` 매핑 저장소
- Flow PDF 톤을 반영한 React 프로토타입(`../core-frontend`)과 브라우저 검증 경로
- 홈/상세/스크랩/아카이브를 하나의 모바일 목업 UI로 확인할 수 있는 데모 화면
- Kakao 시작 CTA와 온보딩 수정(narrow 2단계)까지 포함한 프론트 polish 프로토타입

### 제외 또는 후순위
- 실제 Kakao 운영 앱 기준 access token/userinfo/state 검증 완료
- 운영용 인증/인가 체계 전체 완성
- 실서비스 배포 파이프라인
- production-grade observability
- 실시간 피드 생성 파이프라인

## 5. 현재 구현된 API 책임
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
- `GET /v1/users/{user_id}/archives?month=YYYY-MM`
- `GET /v1/users/{user_id}/archives/{archive_date}`
- `POST /v1/summaries`

## 6. 아키텍처 결정
### 6.1 구조
- `domain/`: 엔티티, enum, 예외, repository interface
- `application/`: 유스케이스/서비스 orchestration
- `infrastructure/`: SQLAlchemy, DB, repository 구현, seed
- `presentation/`: FastAPI route, dependency, request/response schema

### 6.2 모델링 원칙
- dataclass 대신 Pydantic 중심으로 통일
- presentation과 domain 경계 모두 typed model 유지
- 요약 응답은 backend가 마지막에 schema validation을 다시 수행

### 6.3 데이터 저장소
- local Postgres 사용
- Docker Compose로 로컬 실행
- Alembic migration으로 스키마 관리
- pre-Alembic DB는 `stamp head` 호환 로직 유지

### 6.4 요약 연동 원칙
- `../news_summurizer`는 순수 요약 라이브러리로 사용
- core-backend는 요약 API surface만 제공
- 요약 길이 계약 위반 시 `502 summary_contract_violation` 반환

## 7. 완료된 요구사항
- [x] 상위 레벨에 `core-backend` 생성
- [x] FastAPI 기반 백엔드 골격 구축
- [x] PDF 기준 Annoying Cap 브랜딩 반영
- [x] REST 자원 중심 API 초안 제공
- [x] local Postgres + Docker Compose 적용
- [x] DDD + layered architecture 적용
- [x] domain/presentation 모델을 Pydantic 중심으로 통일
- [x] Alembic migration 도입
- [x] 실제 uvicorn 서버 기동 및 주요 엔드포인트 검증
- [x] `../news_summurizer` 연동 `/v1/summaries` 구현
- [x] summary contract violation 시 표준 502 응답 정리
- [x] summary gateway typed boundary 테스트 추가
- [x] `/v1/auth/session` placeholder contract 추가
- [x] auth state / user identity / summary lifecycle / summary sequence 설계 문서 추가
- [x] 실제 Kakao OAuth start/callback/session contract 추가
- [x] callback redirect + `HttpOnly` JWT access/refresh cookie 흐름 추가
- [x] `provider_subject -> internal user_id` 매핑 저장소 및 Alembic migration 추가
- [x] signed OAuth state 발급/검증 추가
- [x] auth application domain을 `app/application/auth/` 하위로 분리
- [x] refresh token 해시 저장 + session metadata(`issued_at`, `last_used_at`, `revoked_at`) 적용
- [x] 온보딩 preference validation: wide/narrow 완료 규칙과 중복 금지 적용
- [x] Flow PDF 기준 피드 블록 정렬/가중치 기본 정책 적용

## 8. 현재 남은 과제
### 후순위 고도화 백로그
- [ ] 현재 점감 weight 정책을 사용자 반응/스크랩 신호까지 반영하는 도메인 정책으로 승격
- [ ] 사용자 행동 로그/스크랩/열람 빈도를 반영한 개인화 점수 모델 추가
- [ ] 개인화 실험용 feature flag 또는 배치 점수 계산 경로 설계

### 중간 우선순위
- [ ] summary ingest/backoffice 운영 플로우 구체화
- [ ] Step 4/요약 실패 `_error`를 backend 표준 에러 매핑과 더 정교하게 연결
- [ ] dev/test/prod seed 전략 분리
- [ ] OpenAPI 예시 및 실패 응답 문서 강화

### 낮은 우선순위
- [ ] 관측성(logging/metrics/tracing) 도입
- [ ] 운영 배포 기준 문서화

## 9. 검증 기준
### 코드/런타임
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')`
- DB-backed TestClient smoke test 통과
- `python3.11 -m alembic upgrade head`
- `python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8030`
- `/health`, `/v1/auth/kakao/start`, `/v1/auth/session`, `/v1/categories`, `/v1/summaries` 실제 HTTP 확인

### 제품 관점
- 온보딩 규칙(Wide/Narrow)이 API 레벨 validation으로 표현되어야 함
- 기사 상세/스크랩/아카이브가 PDF 플로우와 일치해야 함
- 요약 응답은 길이 계약과 사실검증 정책을 깨지 않아야 함

## 10. 문서 운영 규칙
- 진행 상황은 `.dev/progress-log.md`에 시계열로 기록
- 현재 상태와 다음 작업은 `.dev/current-status.md`에 유지
- 실행 계획은 `.dev/plans/` 아래에 보관
- 요구사항/범위 변화는 이 PRD에 먼저 반영
