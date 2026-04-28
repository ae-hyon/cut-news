# Annoying Cap Auth and Summary Flow Implementation Plan

> For Hermes: follow TDD for any production-code changes derived from this plan.

작성 시각: 2026-04-28 01:53:42 KST

목표:
- `../어노잉캡-Flow.pdf` 기준으로 core-backend가 온보딩 이후 로그인, 사용자 식별, 홈/상세에서의 요약 호출 시점을 일관되게 설명하고 구현할 수 있도록 단계별 실행 계획을 만든다.

아키텍처 방향:
- 인증은 당장 실제 Kakao OAuth 전체 구현보다 "서버 경계와 상태 모델을 먼저 고정"하는 순서로 진행한다.
- 요약은 `../news_summurizer`를 직접 호출하는 현재 구조를 유지하되, 어떤 유스케이스에서 어떤 입력으로 `/v1/summaries` 또는 내부 adapter 호출이 발생하는지 명시적으로 연결한다.
- API 계약은 유지하고, 구현은 최소 변경으로 시작한다.

관련 문서:
- `.dev/PRD.md`
- `.dev/current-status.md`
- `README.md`
- `../어노잉캡-Flow.pdf`
- `../news_summurizer/README.md`

---

## Phase 1. 로그인/유저 식별 요구사항 정리

### Task 1: PDF 기준 로그인 상태 전이 문서화
목표:
- 온보딩 완료 → 로그인 유도 → 홈 진입 플로우를 서버 관점 상태로 정리한다.

파일:
- Modify: `.dev/PRD.md`
- Modify: `.dev/current-status.md`
- Create or Modify: `.dev/design/auth-state-machine.md`

할 일:
1. 온보딩 미완료 / 온보딩 완료 미로그인 / 로그인 완료 상태를 정의한다.
2. 각 상태에서 허용되는 API를 표로 정리한다.
3. user_id가 현재 demo 성격인지, 추후 Kakao subject로 치환될지 명시한다.
4. 현재 구현이 실제 인증 없이도 어떤 가정으로 동작하는지 적는다.

검증:
- 문서를 읽는 사람 입장에서 "로그인 전/후에 어떤 API를 써야 하는지" 혼동이 없어야 한다.

### Task 2: 사용자 식별자 정책 고정
목표:
- `user_id`가 현재 어떻게 생성/입력되고, 추후 어떤 외부 ID로 대체될지 정리한다.

파일:
- Create: `.dev/design/user-identity-policy.md`
- Modify: `.dev/PRD.md`

할 일:
1. 현재 `demo-user` 기반 로컬 검증 정책 기록
2. 추후 Kakao 로그인 도입 시 매핑 정책 초안 기록
3. DB에 저장해야 할 최소 사용자 필드 정의
4. anonymous / onboarded / authenticated 사용자를 구분하는 용어 고정

검증:
- 이후 실제 auth 구현 시 DB schema와 API path를 뒤엎지 않아도 되는 수준으로 정리되어야 한다.

---

## Phase 2. 요약 호출 시점 명세화

### Task 3: 홈/상세/스크랩/아카이브에서 요약 데이터의 출처 정의
목표:
- 각 화면이 "이미 저장된 summary를 읽는지" 또는 "실시간 summarize를 호출하는지" 결정한다.

파일:
- Create: `.dev/design/summary-lifecycle.md`
- Modify: `.dev/PRD.md`
- Modify: `README.md`

할 일:
1. 홈 피드 카드가 요구하는 summary 필드 정리
2. 기사 상세가 요구하는 summary/content/original_url 관계 정리
3. 스크랩/아카이브가 기존 summary를 재사용하는지 명시
4. `/v1/summaries`를 사용자 앱 runtime endpoint로 둘지, 내부 운영/백오피스/ingest용으로 둘지 결정안 작성

검증:
- 어떤 요청이 들어오면 summary를 새로 생성하고, 어떤 요청은 기존 summary만 읽는지 한눈에 보여야 한다.

### Task 4: summary 연동 시퀀스 다이어그램 초안 작성
목표:
- core-backend → news_summurizer 호출 경로를 텍스트 시퀀스로 문서화한다.

파일:
- Create: `.dev/design/summary-sequence.md`

할 일:
1. API request → presentation schema → application service → adapter → summarizer → validation → response 흐름 작성
2. contract violation 시 502가 발생하는 분기 기록
3. `_error` 산출물과 backend error payload의 관계 기록

검증:
- 새 사람이 읽어도 `/v1/summaries` 실패 경로를 바로 이해할 수 있어야 한다.

---

## Phase 3. 최소 구현 보강

### Task 5: summary gateway를 typed boundary로 고정하는 테스트 추가
목표:
- summary service가 dict soup가 아니라 `news_schema` 기반 boundary를 사용함을 보장하는 테스트를 만든다.

파일:
- Create: `tests/test_summary_gateway.py`
- Modify: `app/application/services/summary_service.py`

TDD:
1. failing test 작성: service가 payload를 `NewsArticle`, `SummarizeRequest`, `SummarizerSettings`로 변환하는 경로를 검증
2. 테스트 실행해 실패 확인
3. 최소 구현 수정
4. 테스트 재실행
5. 전체 smoke test 재실행

검증 명령:
- `pytest tests/test_summary_gateway.py -q`
- `python3.11 -m py_compile $(find app -name '*.py' | tr '\n' ' ')`

### Task 6: auth placeholder boundary 추가 여부 결정
목표:
- 실제 Kakao OAuth 전이라도 auth 관련 API placeholder를 둘지 결정하고, 두는 경우 최소 contract를 만든다.

파일 후보:
- Create: `app/presentation/api/routes/auth.py`
- Modify: `app/presentation/api/router.py`
- Modify: `app/presentation/schemas.py`
- Test: `tests/test_auth_routes.py`

선택지:
- A안: 아직 라우트는 만들지 않고 `.dev` 설계 문서만 유지
- B안: `/v1/auth/session` 또는 `/v1/auth/kakao/callback` placeholder contract만 추가

결정 기준:
- 프론트/클라이언트가 곧 붙는다면 B안
- 아직 요구사항 정리 단계면 A안

---

## Phase 4. 문서와 검증 동기화

### Task 7: README와 .dev 문서 동기화
목표:
- README는 실행 기준, `.dev`는 설계/상태/계획 역할로 분리한다.

파일:
- Modify: `README.md`
- Modify: `.dev/current-status.md`
- Modify: `.dev/progress-log.md`

할 일:
1. README에는 현재 구현/실행 방법만 남긴다.
2. `.dev/current-status.md`에는 다음 우선순위를 유지한다.
3. 실제 작업이 진행될 때마다 progress log에 시계열로 추가한다.

검증:
- README를 읽으면 "어떻게 실행하는지"가 보이고
- `.dev`를 읽으면 "왜 이렇게 되어 있고 다음엔 뭘 하는지"가 보여야 한다.

---

## 우선 실행 권장 순서
1. Task 1
2. Task 2
3. Task 3
4. Task 4
5. Task 5
6. Task 6
7. Task 7

## 즉시 다음 액션 추천
- 문서 우선이면: Task 1부터 4까지 먼저 완료
- 구현 우선이면: Task 5부터 바로 시작

## 완료 정의
- `.dev` 아래에서 auth / user identity / summary lifecycle / sequence 문서를 찾을 수 있어야 한다.
- summary 경계 테스트가 있어야 한다.
- README와 `.dev`의 역할 분담이 명확해야 한다.
