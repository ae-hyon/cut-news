# Auth State Machine

최종 갱신: 2026-04-28 02:13:14 KST

## 목적
`../어노잉캡-Flow.pdf` 기준의 온보딩 완료 → 로그인 유도 → 홈 진입 흐름을 현재 core-backend가 어떻게 수용하는지 서버 상태 모델로 고정한다.

## 현재 서버 상태 정의

### 1. anonymous
의미:
- 클라이언트가 아직 `user_id`를 제시하지 않은 상태
- 서버는 특정 사용자를 식별하지 못한다
- 실제 OAuth 세션도 없다

판단 기준:
- `GET /v1/auth/session` 호출 시 `user_id` query parameter가 없으면 `anonymous`

응답 예시:
- `user_id=null`
- `session_state=anonymous`
- `onboarding_completed=false`
- `authenticated=false`
- `auth_provider=none`

허용 API:
- `GET /health`
- `GET /v1/categories`
- `GET /v1/categories/{slug}`
- `GET /v1/auth/session`
- `POST /v1/summaries` (운영/백엔드용 요약 경계 테스트 및 내부 호출용)

### 2. onboarded
의미:
- 사용자는 로컬 식별자(`user_id`)를 가지고 있다
- 온보딩/선호 저장이 완료되어 홈 진입에 필요한 기본 데이터가 있다
- 아직 실제 외부 인증 공급자 세션은 없다
- 현재 backend는 이 상태를 홈 진입 가능한 최소 상태로 본다

판단 기준:
- `GET /v1/auth/session?user_id=...` 호출 시 `service.get_preferences(user_id).onboarding_completed == true`

응답 예시:
- `user_id=demo-user`
- `session_state=onboarded`
- `onboarding_completed=true`
- `authenticated=false`
- `auth_provider=demo`

허용 API:
- anonymous 상태의 허용 API 전체
- `GET /v1/users/{user_id}/preferences`
- `PUT /v1/users/{user_id}/preferences`
- `GET /v1/users/{user_id}/feed`
- `GET /v1/articles/{article_id}?user_id=...`
- `PUT /v1/users/{user_id}/scraps/{article_id}`
- `DELETE /v1/users/{user_id}/scraps/{article_id}`
- `GET /v1/users/{user_id}/scraps`
- `GET /v1/users/{user_id}/archives?month=YYYY-MM`
- `GET /v1/users/{user_id}/archives/{archive_date}`

### 3. authenticated
의미:
- 추후 Kakao OAuth가 연결되면 도달할 최종 상태
- 현재 저장소에서는 실제로 생성되지 않는다
- 문서/응답 계약에는 reserved state로만 남겨 둔다

예상 판단 기준:
- 서버가 provider session 또는 signed token을 검증하고
- 그 provider subject를 내부 사용자 레코드에 매핑할 수 있을 때

예상 응답 필드:
- `session_state=authenticated`
- `authenticated=true`
- `auth_provider=kakao`
- `provider_subject=<kakao subject>`

## 상태 전이
1. anonymous -> onboarded
- 사용자가 온보딩을 완료하고 `PUT /v1/users/{user_id}/preferences`로 선호를 저장
- 이 시점에 `onboarding_completed=true`

2. onboarded -> authenticated
- 현재 미구현
- 추후 Kakao 로그인 callback/session 교환 후 전이 예정

3. authenticated -> onboarded or anonymous
- 현재 미구현
- 추후 로그아웃/세션 만료 정책에서 정의 예정

## 현재 구현의 핵심 해석
- 프론트에서 로그인 버튼을 보여주더라도, 현재 백엔드는 실제 OAuth 없이 `user_id` 기반 demo session으로 앱 주요 기능을 사용할 수 있다.
- 즉, 현재 홈/상세/스크랩/아카이브는 엄밀한 인증 완료보다 "온보딩된 로컬 사용자 식별"에 의존한다.
- 따라서 현재 `/v1/auth/session`은 인증 완성체가 아니라 상태 확인용 placeholder boundary다.

## 서버 관점 권장 사용 순서
1. 앱 시작 시 `GET /v1/auth/session`
2. `anonymous`면 온보딩 진행
3. 온보딩 저장 후 `GET /v1/auth/session?user_id=<local-user-id>` 또는 직접 사용자 API 진입
4. 현재 버전에서는 `onboarded` 상태를 홈 진입 가능 상태로 사용
5. 추후 Kakao 연동 후에는 `authenticated` 상태를 추가 검증 포인트로 승격
