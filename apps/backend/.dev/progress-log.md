
## 2026-04-28 18:09 KST — PDF 앱 내부 화면 기준으로 프론트 재정렬
실행:
- `어노잉캡-Flow.pdf`를 `.pdf-reference/flow-full.png` / `flow-overview.png`로 렌더링
- `.pdf-reference/screens/`에는 1차 phone mock crop 저장, `.pdf-reference/app-screens/`에는 베젤 안쪽 앱 화면 기준 2차 crop 저장
- `.pdf-reference/README.md`에 구현 기준 명시: 폰 베젤/status bar/browser bar/home indicator는 구현 금지, 앱 내부 콘텐츠만 구현
- 잘못 추가된 Safari/status/home-indicator frame을 `AppShell.tsx`와 `layout.css`에서 제거
- 기본 화면을 393px 앱 내부 캔버스로 변경하고, 검정 배경/Annoying Cap/26.04.07/스크랩|아카이브/선택 카드/주황 CTA 중심으로 정리
- body/app 배경의 radial/gradient 반사광 제거
- 홈 화면을 PDF 스타일의 2열 rounded text card grid로 재정렬

검증:
- `npm run typecheck && npm run build` 통과
- browser에서 시작 화면과 홈 화면 확인
- DOM 기준 `.app-canvas` width 393px, `.safari-frame/.ios-statusbar/.safari-toolbar/.home-indicator` 없음 확인
- `body` background-image `none` 확인
- browser vision 기준 폰 베젤/status/browser bar 없이 앱 내부 화면만 보임 확인

남은 작업:
- 현재 backend demo feed에 PDF와 무관한 `AI/카카오 로그인` 카드가 남아 있어, PDF 동일 검증용 seed/display data로 교체 필요
- `.pdf-reference/app-screens` crop 일부는 원본 캔버스 특성상 빗나간 부분이 있어, 화면별 기준 이미지는 추가 수동 보정 필요
- 상세/스크랩/아카이브 화면도 기준 crop과 대조하며 카드 density/문구/간격을 추가 조정 필요


## 2026-04-28 17:30 KST — Kakao 시작 UX 자동 session 재확인 개선
실행:
- `useAuthSession.ts`에 `kakaoAuthStatus` / `kakaoAuthPending` 상태 추가
- `카카오로 시작하기` 클릭 시 popup을 열고 waiting 상태/사용자 안내 표시
- 현재 창 focus/visibility 복귀 시 `GET /v1/auth/session`을 silent 재확인하도록 `usePrototypeApp.ts`에 listener 연결
- 수동 `로그인 완료 확인` 버튼은 명시적으로 `app.checkKakaoSession()` wrapper를 사용하도록 수정
- React click event가 `silent` 인자로 잘못 전달되어 수동 확인 안내가 갱신되지 않던 버그 수정
- session 확인 성공 시 onboarding 완료 여부에 따라 홈/관심사로 routing하는 기존 `loadUserState` 규칙 재사용

검증:
- `npm run typecheck && npm run build` 통과
- browser에서 `window.open` stub으로 Kakao popup 호출, waiting 안내 표시 확인
- focus 복귀 silent session check 동작 확인
- 수동 `로그인 완료 확인`에서 anonymous 상태일 때 사용자-facing 실패 안내 표시 확인
- 데모 홈 진입, bottom nav, 430px canvas, natural scroll 확인
- browser console JS error/warning 없음

남은 작업:
- 실제 Kakao 계정으로 callback 완료 후 cookie/session 반영 수동 E2E 검증
- callback JSON 화면을 사용자에게 보이지 않게 만드는 운영 UX는 프론트/백엔드 계약 확정 후 별도 마감


## 2026-04-28 17:17 KST — 프론트 view-state reducer 도입
실행:
- `src/hooks/useViewState.ts` 추가
- `activeTab` 직접 state를 reducer 기반 `GO_TAB / OPEN_DETAIL / CLOSE_DETAIL / RESET_TO_HOME / RESET_TO_ONBOARDING` action으로 교체
- 상세 화면은 `isDetailOpen` view-state로 판단하고, 뒤로가기는 `closeArticle` action으로 통일
- 하단 nav는 상세 화면에서 숨기고 탭 전환 시 상세 상태를 닫도록 정리

검증:
- `npm run typecheck` 통과
- `npm run build` 통과
- browser console 기준 새 JS error/warning 없음
- DOM 기준 데모 홈 진입 -> 상세 보기 -> 홈으로 -> 스크랩 -> 아카이브 -> 관심사 전환 확인
- 상세 화면에서 bottom nav 숨김, 복귀 후 bottom nav 표시 확인
- app width 430px, natural scroll 확인

남은 작업:
- Kakao callback 완료 후 자동 세션 반영 UX 검증/개선
- NewsCard variant/action 일반화
- 실제 모바일/PWA 설치 검증


## 2026-04-28 17:06 KST — 프론트 hook 추가 분리 및 warning-free 검증
실행:
- `useAuthSession.ts` 추가: health/session/Kakao bootstrap/auth notice 분리
- `useContentFeed.ts` 추가: feed/detail/scrap 상태와 refresh 분리
- `useArchiveState.ts` 추가: archive month/date 상태 분리
- `usePrototypeApp.ts`를 auth/content/archive/preference hook 조립 orchestration으로 축소
- HomeScreen list key를 `block_id + index/article_id` 조합으로 보강해 React key warning 제거

검증:
- `npm run typecheck && npm run build` 통과
- browser console 기준 새 JS error 없음
- browser DOM 기준 데모 홈 진입, 상세 보기, 홈 복귀, 아카이브 탭, 관심사 탭 확인
- app width 430px, scrollHeight > clientHeight 확인

남은 작업:
- Kakao callback 완료 후 자동 세션 반영 UX를 실제 OAuth 환경에서 검증
- view-state reducer 도입 여부 검토
- 실제 모바일/PWA 설치 검증


## 2026-04-28 16:53 KST — 프론트 hook/service 분리 및 UI polish 추가
실행:
- `src/services/backendApi.ts` 추가: health/session/kakao/preferences/feed/article/scrap/archive 호출을 typed 함수로 분리
- `src/hooks/usePreferenceSelection.ts` 추가: wide/narrow 선택 상태, subcategory map, preference payload 변환 분리
- `usePrototypeApp.ts`를 app-level orchestration 중심으로 축소
- 시작 hero, Kakao CTA, news card shadow/radius, bottom nav 질감 polish
- bottom nav가 마지막 카드와 겹치지 않도록 app shell 하단 padding 확대

검증:
- `npm run typecheck && npm run build` 통과
- browser에서 시작 화면, demo 홈, 아카이브 탭, 430px app width, scrollHeight > clientHeight 확인
- browser vision 기준 debug/sandbox 패널 없이 중앙 모바일/PWA 앱 화면으로 보임 확인

남은 작업:
- 실 Kakao callback 완료 후 자동 세션 반영 UX
- 실제 모바일 Safari/Chrome PWA 설치 검증
- PDF와 1:1에 더 가까운 아이콘/타이포/간격 polish


## 2026-04-28 16:41 KST — 프론트 TSX/TypeScript 전환
실행:
- React 컴포넌트 `.jsx`를 `.tsx`로 전환
- hook/lib `.js`를 `.ts`로 전환
- `tsconfig.json`, `tsconfig.node.json`, `src/vite-env.d.ts` 추가
- `src/lib/types.ts`에 backend API/domain 타입 추가
- `package.json`에 `typecheck` 스크립트 추가, `build`가 `tsc --noEmit && vite build`를 수행하도록 변경
- `index.html` entrypoint를 `/src/main.tsx`로 변경

검증:
- `npm run typecheck` 통과
- `npm run build` 통과
- browser에서 시작 화면, 데모 홈, 아카이브 탭, PWA manifest/service worker 등록 확인

결정:
- 완성본 기준 프론트는 JSX가 아니라 TSX/TypeScript로 관리한다.
- 화면 컴포넌트 props는 `src/lib/types.ts`와 hook exported type을 재사용한다.

# Annoying Cap Core Backend Progress Log

## 2026-04-28 16:18 KST — PWA형 고정 모바일 캔버스 전환 및 사용자용 라벨 정리
실행:
- `core-frontend`에서 sandbox/phone mock 렌더링 잔재(`BoardRail`, `PhoneFrame`, `RuntimeStatus`) 제거
- `AppShell` 기준으로 웹에서는 430px 중앙 고정 앱 캔버스, 430px 이하 모바일에서는 100vw로 동작하도록 CSS 재구성
- `manifest.webmanifest`, `icon.svg`, mobile meta/theme-color 추가
- 기본 사용자 화면에서 debug/session/API 상태 패널을 제거하고 `?debug=1` 전용 `DevPanel`로 이동
- 홈 피드의 `WEIGHT`, `Block`, 영문 카테고리 태그를 사용자용 `추천순`, `경제/정치/테크`, `관심사` 라벨로 정리

검증:
- `npm run build` 통과
- browser에서 app width 430px, bottom nav width 406px, scrollHeight > clientHeight 확인
- browser DOM 기준 홈/관심사/스크랩/아카이브 탭 전환 확인
- 사용자 화면에 `WEIGHT`, `Block`, `debug`, `session_state`, `API/Session/User`, `anonymous/guest`가 노출되지 않음 확인

판단:
- 프론트는 더 이상 sandbox 화면이 아니라, PDF 해상도에 맞춘 웹/PWA용 중앙 고정 모바일 앱 화면으로 동작한다.
- 남은 작업은 실 Kakao callback 완료 UX, 아이콘/타이포 세부 polish, 실제 기기 PWA 설치 검증이다.

## 2026-04-28 01:53 KST — .dev 문서 관리 체계 추가
실행:
- `../어노잉캡-Flow.pdf` 기준 핵심 요구사항 재정리
- `core-backend`용 제품 요구사항 문서 초안 작성
- 현재 구현 상태/다음 작업을 추적할 수 있도록 `.dev/current-status.md` 작성
- 시계열 기록용 `.dev/progress-log.md` 생성

산출물:
- `.dev/PRD.md`
- `.dev/current-status.md`
- `.dev/progress-log.md`

정리한 핵심 요구사항:
- Wide/Narrow 온보딩 구분
- Wide: 대분류 최소 3개, 최대 5개
- Narrow: 대분류 1개 + 중카테고리 여러 개
- 홈 피드 블록 구조 및 AI 가중치 기반 비중
- 기사 상세/스크랩/아카이브 흐름
- `../news_summurizer` 연동 요약 API

현재 판단:
- `core-backend`는 이미 주요 API와 로컬 실행 기반은 갖춰져 있음
- 앞으로는 제품 플로우 구체화, 인증/로그인 설계, summary 연동 운영 정책 문서화가 다음 초점임

## 2026-04-28 01:54 KST — 다음 단계 실행 계획 추가
실행:
- `.dev/plans/2026-04-28-auth-and-summary-flow.md` 생성
- 로그인/유저 식별 정책과 summary 호출 시점을 분리해 문서화/구현할 수 있도록 Phase 기반 계획 작성
- 문서 우선 단계(Phase 1~2)와 구현 우선 단계(Phase 3)를 구분

산출물:
- `.dev/plans/2026-04-28-auth-and-summary-flow.md`

판단:
- 지금은 실제 OAuth 코드를 바로 넣기보다 상태 모델과 summary lifecycle을 먼저 고정하는 편이 안전함
- 이후 구현 작업은 이 계획 문서를 기준으로 순차 진행 가능

## 2026-04-28 02:13 KST — Phase 1~4 백엔드 구현/문서 정리 완료
실행:
- `.dev/design/auth-state-machine.md` 작성
- `.dev/design/user-identity-policy.md` 작성
- `.dev/design/summary-lifecycle.md` 작성
- `.dev/design/summary-sequence.md` 작성
- `/v1/auth/session` placeholder route 추가
- `AuthSessionResponseSchema` 추가
- `SummaryGatewayService`를 API schema/Pydantic payload를 받아 summarizer typed model로 변환하는 경계로 정리
- `tests/test_summary_gateway.py`, `tests/test_auth_routes.py` 추가
- summary route가 typed result를 API response schema로 마지막 검증하도록 정리
- README, PRD, current-status 갱신

산출물:
- `.dev/design/auth-state-machine.md`
- `.dev/design/user-identity-policy.md`
- `.dev/design/summary-lifecycle.md`
- `.dev/design/summary-sequence.md`
- `app/presentation/api/routes/auth.py`
- `app/presentation/schemas.py`
- `app/presentation/api/router.py`
- `app/application/services/summary_service.py`
- `app/presentation/api/routes/summaries.py`
- `tests/test_summary_gateway.py`
- `tests/test_auth_routes.py`
- `README.md`
- `.dev/PRD.md`
- `.dev/current-status.md`

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8010` 기동 후
  - `GET /health` 200 확인
  - `GET /v1/auth/session` 200 확인
  - `GET /v1/auth/session?user_id=demo-user` 200 확인
  - `GET /v1/categories` 200 확인
  - `POST /v1/summaries` 실제 요약 응답 200 확인

판단:
- 현재 백엔드는 온보딩/피드/기사/스크랩/아카이브/요약 경계를 모두 문서와 코드로 고정한 상태다.
- 실제 OAuth는 아직 없지만, 사용자 상태 조회와 future Kakao 매핑을 수용할 placeholder 경계는 확보했다.
- 현재 제품 단계에서 백엔드 파트는 로컬 개발/시연 기준으로 마무리 가능한 수준이다.

## 2026-04-28 08:33 KST — Kakao OAuth 경계와 internal user mapping 추가
실행:
- `.dev/plans/2026-04-28-kakao-oauth-implementation.md` 작성
- `tests/test_auth_routes.py`, `tests/test_auth_service.py`로 Kakao start/callback/session RED 테스트 추가
- `tests/test_user_preference_repository.py`로 신규 user preference flush 버그 재현 테스트 추가
- `app/application/services/auth_service.py` 추가
- `app/domain/entities.py`, `app/domain/repositories.py`에 `ExternalIdentity`, `AuthSession`, `ExternalIdentityRepository` 추가
- `app/infrastructure/models.py`, `app/infrastructure/repositories.py`에 `external_identities` 저장소 구현 추가
- `alembic/versions/0002_external_identities.py` 추가
- `app/presentation/api/routes/auth.py`, `app/presentation/api/dependencies.py`, `app/presentation/schemas.py`를 Kakao auth contract 기준으로 갱신
- `SqlAlchemyUserPreferenceRepository.save()`의 신규 row flush 버그 수정
- README, PRD, current-status 문서 갱신

산출물:
- `.dev/plans/2026-04-28-kakao-oauth-implementation.md`
- `app/application/services/auth_service.py`
- `alembic/versions/0002_external_identities.py`
- `tests/test_auth_routes.py`
- `tests/test_auth_service.py`
- `tests/test_user_preference_repository.py`

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `python3.11 -m alembic upgrade head` 통과
- DB-backed `AuthService.complete_kakao_callback()` / `resolve_session()` 확인
- `PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8011` 기동 후
  - `GET /v1/auth/kakao/start` 200 확인
  - `GET /v1/auth/session` anonymous 200 확인
  - `GET /v1/auth/session?user_id=demo-user` onboarded 200 확인
  - `GET /v1/auth/session?provider=kakao&provider_subject=runtime-kakao-001` authenticated 200 확인

판단:
- 이제 auth 경계는 placeholder를 넘어서 Kakao provider subject를 내부 user_id와 연결하는 수준까지 올라왔다.
- 아직 남은 핵심은 실제 access token 검증 정책과 세션 쿠키를 더 안전한 형태로 승격하는 일이다.

## 2026-04-28 10:28 KST — refresh token hash 저장으로 보안 강화
실행:
- `tests/test_auth_service.py`에 refresh token 원문 미저장 RED 테스트 추가
- `app/domain/entities.py`의 `RefreshSession`을 `refresh_token_hash` + `issued_at` / `last_used_at` / `revoked_at` 구조로 변경
- `app/application/auth/token_service.py`에 SHA-256 hash 생성, hash 기반 refresh 조회/폐기 로직 추가
- `app/infrastructure/models.py`, `app/infrastructure/repositories.py`를 hash 컬럼 및 metadata 기준으로 갱신
- `alembic/versions/0004_refresh_session_hashes.py` 추가, 기존 refresh token 데이터 해시 마이그레이션 반영
- current-status, PRD 갱신

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `python3.11 -m alembic upgrade head` 통과

판단:
- 이제 refresh token 원문은 DB에 남지 않고, 토큰 탈취 시 DB dump만으로는 즉시 재사용이 어려워졌다.
- 다음 핵심은 신규 Kakao 유저 onboarding 연결과 운영 로그/실패 taxonomy 정리다.

## 2026-04-28 09:56 KST — auth application domain 분리 + Kakao state 검증 추가
실행:
- `app/application/auth/errors.py`, `kakao_oauth_service.py`, `state_service.py`, `token_service.py`, `query_service.py` 추가
- `app/application/services/auth_service.py`를 얇은 orchestrator façade로 재구성
- Kakao OAuth state를 JWT 서명 토큰으로 발급하고 callback에서 검증하도록 반영
- Kakao token exchange/userinfo fetch 실패를 `AuthError`로 매핑
- auth route에서 `AuthError`를 표준 JSON 에러로 반환하도록 정리
- auth 관련 테스트를 state 위변조/교환 실패 시나리오까지 확장
- README, `.env`, `.env.example`, current-status, PRD 갱신

검증:
- `PYTHONPATH=. python3.11 -m pytest tests/test_auth_service.py tests/test_auth_routes.py -q` 통과
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `python3.11 -m alembic upgrade head` 통과

판단:
- auth 책임을 Kakao OAuth / state 검증 / JWT token / session query 축으로 분리해서 이후 Apple/Google 확장이나 refresh 저장 강화 작업이 쉬워졌다.
- 현재 남은 핵심은 refresh token 저장 강화를 운영 수준으로 끌어올리고, 신규 유저 onboarding 연결을 완결하는 것이다.

## 2026-04-28 09:20 KST — JWT access + refresh token 인증 구조로 전환
실행:
- `PyJWT` 의존성 추가
- `app/domain/entities.py`, `app/domain/repositories.py`에 `RefreshSession`, `AuthTokens`, `RefreshSessionRepository` 추가
- `app/infrastructure/models.py`, `app/infrastructure/repositories.py`에 `refresh_sessions` 저장소 구현 추가
- `alembic/versions/0003_refresh_sessions.py` 추가 후 `alembic upgrade head` 적용
- `app/application/services/auth_service.py`를 JWT access token 발급 + DB-backed refresh rotation 구조로 재작성
- `app/presentation/api/routes/auth.py`에 `POST /v1/auth/refresh`, `POST /v1/auth/logout` 추가
- `/v1/auth/session`이 access token cookie를 우선 사용하도록 변경
- `tests/test_auth_service.py`, `tests/test_auth_routes.py`를 JWT 흐름 기준으로 확장
- README, `.env.example`, `.env`, current-status, PRD 갱신

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `python3.11 -m alembic upgrade head` 통과
- `PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8013` 기동 후
  - JWT access cookie로 `GET /v1/auth/session` authenticated 200 확인
  - refresh cookie로 `POST /v1/auth/refresh` 200 + access/refresh cookie rotation 확인
  - refresh cookie로 `POST /v1/auth/logout` 200 + cookie clear 확인

판단:
- 이제 인증 경계는 단순 cookie 문자열이 아니라 backend-issued JWT access token + DB-backed refresh token 구조로 정리됐다.
- 남은 핵심은 실제 Kakao access token/state 검증과 refresh token 저장 강화를 운영 기준으로 다듬는 일이다.

## 2026-04-28 08:58 KST — backend-owned redirect + cookie session 흐름 반영
실행:
- `tests/test_auth_routes.py`에 callback redirect + cookie session RED 테스트 추가
- `app/presentation/api/routes/auth.py`에서 Kakao callback이 프론트 성공 페이지로 redirect 하며 `HttpOnly` 쿠키를 설정하도록 변경
- `/v1/auth/session`이 query param 없을 때도 `annoyingcap_session` 쿠키를 읽어 authenticated 세션을 복원하도록 변경
- `app/common/config.py`에 `FRONTEND_BASE_URL`, `AUTH_SESSION_COOKIE_*` 설정 추가
- README, current-status, PRD를 cookie session 흐름 기준으로 정리

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8012` 기동 후
  - `GET /v1/auth/kakao/start` 200 확인
  - cookie `annoyingcap_session=kakao:runtime-kakao-001`로 `GET /v1/auth/session` authenticated 200 확인
  - `GET /health` 200 확인
- callback redirect + `Set-Cookie: annoyingcap_session=...; HttpOnly`는 TestClient로 검증

판단:
- 프론트는 Kakao 토큰 교환 세부사항을 몰라도 로그인 시작과 세션 조회만으로 상태를 사용할 수 있는 구조가 됐다.
- 다만 현재 cookie 값은 단순 문자열이므로 운영 전에는 서명/암호화 또는 서버측 세션 저장으로 바꾸는 것이 좋다.

## 2026-04-28 11:20 KST — frontend 비의존 auth callback + onboarding session_state 정리
실행:
- `tests/test_auth_routes.py`를 callback redirect 기대값 대신 JSON + cookie 응답 기준으로 수정
- onboarding 완료 유저의 auth session 상태를 `onboarded`로 유지하도록 query/token 경계를 정리
- `app/presentation/api/routes/auth.py`에서 Kakao callback이 redirect 없이 `AuthSessionResponseSchema` JSON과 `HttpOnly` 쿠키를 반환하도록 수정
- `app/common/config.py`, `.env`, `.env.example`에서 프론트 URL 의존 설정 제거
- README, current-status, PRD를 “백엔드는 API만 제공, 프론트는 session_state로 라우팅” 기준으로 정리

검증:
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과

판단:
- 백엔드는 프론트 URL이나 라우팅 규칙을 몰라도 되고, React 프론트가 `session_state`를 보고 온보딩/홈 이동을 결정하는 계약으로 정리됐다.
- auth 책임은 API 경계, 쿠키 발급, state/token 검증으로 한정되고 프론트 라우팅 지식은 제거됐다.


## 2026-04-28 11:42 KST — onboarding validation 계약 강화
실행:
- `tests/test_user_service.py`, `tests/test_user_routes.py` 추가
- wide 모드에서 subcategory payload 금지, primary 중복 금지 규칙을 RED/GREEN으로 추가
- narrow 모드에서 subcategory 중복 금지 규칙을 RED/GREEN으로 추가
- 유효한 preference 저장 시 `onboarding_completed=True`가 유지되도록 route/service 검증 강화
- README, current-status, PRD에 온보딩 validation 규칙 반영

검증:
- `PYTHONPATH=. python3.11 -m pytest tests/test_user_service.py tests/test_user_routes.py -q` 통과
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '
' ' ')` 통과

판단:
- 이제 온보딩 완료는 단순 preference 저장이 아니라, wide/narrow 계약을 만족하는 유효한 선택일 때만 성립한다.
- 프론트는 여전히 backend validation 결과와 `onboarding_completed`/`session_state`만 보고 흐름을 제어하면 된다.


## 2026-04-28 13:11 KST — 간단한 React 프론트 추가 및 브라우저 검증
실행:
- `../core-frontend`에 React + Vite 프로토타입 생성
- `vite.config.js` proxy로 `/v1`, `/health`를 backend `127.0.0.1:8000`에 연결
- `src/main.jsx`, `src/styles.css`로 Flow PDF 톤의 단일 화면 앱 구현
- `ui-demo-user` 기준으로 `anonymous -> onboarding -> onboarded -> feed` 흐름 확인
- frontend build: `npm run build`

검증:
- `http://127.0.0.1:5173` browser 열람 성공
- 초기 anonymous 상태 표시 성공
- `ui-demo-user` preference 저장 후 backend session이 `onboarded`로 바뀌는 것 확인
- 재시작 후 피드 블록 렌더링(browser snapshot) 확인

판단:
- 실 Kakao UI까지는 아직 붙이지 않았지만, backend API를 실제 브라우저 화면에 연결해 상태/피드 렌더링을 검증할 수 있는 최소 프론트는 확보됨
- 개인화/운영 고도화는 문서 백로그로 남기고 후순위로 미룸

## 2026-04-28 11:54 KST — Flow PDF 기준 피드 가중치/정렬 기본 정책 반영
실행:
- `tests/test_feed_service.py` 추가
- wide 피드가 온보딩 시 선택한 대분류 순서를 보존하고 block weight를 점감시키는 RED/GREEN 테스트 추가
- narrow 피드가 단일 focus block(`weight=1.0`)을 반환하도록 테스트/구현 추가
- 각 block 내부 article이 `score_weight` 내림차순으로 정렬되도록 구현
- `Article` 도메인 모델과 SQLAlchemy 매핑에 `score_weight`를 올림
- README, current-status, PRD에 피드 정책 반영

검증:
- `PYTHONPATH=. python3.11 -m pytest tests/test_feed_service.py -q` 통과
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '
' ' ')` 통과

판단:
- 이제 Flow.pdf의 홈 블록 비중 아이디어가 최소한의 backend 규칙으로 코드화되었다.
- 아직 AI/개인화까지는 아니고, 현재는 온보딩 선택 순서와 article score 기반의 deterministic 정책이다.

## 2026-04-28 13:52 KST — PDF 근접 프론트 확장 및 최종 브라우저 QA
실행:
- `../어노잉캡-Flow.pdf` 1페이지를 이미지로 렌더링하고 시각 분석으로 핵심 레이아웃/톤/컴포넌트 구조를 재정리
- `../core-frontend/src/main.jsx`, `src/styles.css`를 재작성해 단일 온보딩 화면 수준에서 모바일 목업 기반 다중 화면 앱으로 확장
- 홈/상세/스크랩/아카이브를 하단 탭바 안에서 전환되도록 구성
- `ui-demo-user` 기준으로 홈 피드, 기사 상세, 스크랩 추가, 아카이브 월/일 보기까지 browser로 반복 검증
- frontend build 재검증: `npm run build`

검증:
- browser에서 `anonymous -> onboarded -> 홈 피드` 재현 확인
- 기사 상세 진입 확인
- 상세에서 스크랩 추가 후 스크랩 탭 반영 확인
- 아카이브 탭에서 `2026-04` 월과 일별 기사 목록 확인
- `npm run build` 통과

판단:
- 현재 프론트는 PDF의 색감/카드/모바일 목업/하단 탭 구조를 상당 부분 반영한 시연 가능한 프로토타입 수준까지 올라왔다.
- 다만 PDF 완성본 대비 남은 차이는 세밀한 타이포/간격/아이콘/상태 애니메이션/실 Kakao 로그인 UI 연결 등 프레젠테이션 디테일에 가깝다.
- 기능 플로우 관점에서는 온보딩/홈/상세/스크랩/아카이브의 핵심 경로를 실제 백엔드와 붙여 확인한 상태다.


## 2026-04-28 14:20 KST — 프론트 polish: Kakao CTA + narrow 2단계 UX


## 2026-04-28 14:20 KST — 프론트 컴포넌트 구조 정리 및 재사용 원칙 문서화
실행:
- `core-frontend/src`를 `App / hooks / lib / components / styles` 구조로 정리된 상태로 점검
- `NewsCard`, `SectionHeader`, `BottomNav`, `PhoneFrame`, `BoardRail` 등 공통 컴포넌트 재사용 확인
- 사용되지 않는 옛 `src/styles.css` 제거
- `core-frontend/README.md`, `core-frontend/ARCHITECTURE.md`에 파일 구조와 재사용 원칙 문서화
- frontend build 재검증

검증:
- `npm run build` 통과
- browser에서 홈/스크랩/아카이브/온보딩 탭 전환 DOM 검증
- `NewsCard`가 홈/스크랩 양쪽에서 재사용되는 것 확인

판단:
- 현재 프론트는 단일 파일 프로토타입에서 벗어나, 재사용 가능한 컴포넌트와 얇은 진입점/조립 계층을 가진 구조로 정리되었다.
- 이후 디자인 polish를 계속하더라도 화면별 로직과 공통 UI를 분리한 채 유지하기 쉬운 상태다.

실행:
- `core-frontend/src/main.jsx`에 Kakao 시작 URL CTA 연결 (`GET /v1/auth/kakao/start` 응답 사용)
- 온보딩 수정 화면을 별도 탭으로 다시 열 수 있게 정리
- narrow 모드를 `1. 대카테고리 -> 2. 소카테고리` 단계형 UX로 개편
- 하단 탭/CTA 버튼의 히트박스와 간격을 키워 모바일 조작감을 개선
- frontend build 재검증: `npm run build`

검증:
- `npm run build` 통과
- browser DOM에서 하단 탭 active 전환 확인
- 시작 화면에 Kakao CTA 존재 확인
- 홈/상세/스크랩/아카이브 기본 플로우 유지 확인

판단:
- 지금 프론트는 PDF를 그대로 복제한 수준은 아니지만, 기능 데모와 시각 방향성 모두 더 완성본에 가까워졌다.
- 남은 차이는 주로 세부 타이포/아이콘/마이크로 인터랙션/실 Kakao 로그인 callback UX 마감이다.


## 2026-04-28 15:55 KST — 프론트 컴포넌트 구조 정리 및 재사용 원칙 문서화
실행:
- `core-frontend/src/main.jsx` 단일 대형 파일 구조를 `App / hooks / lib / components / styles`로 분리
- `BoardRail`, `PhoneFrame`, `TopBar`, `BottomNav`를 layout/navigation 계층으로 분리
- `NewsCard`, `SectionHeader`를 공통 컴포넌트로 추출해 홈/스크랩/아카이브에서 재사용
- `IntroScreen`, `OnboardingScreen`, `HomeScreen`, `DetailScreen`, `ScrapsScreen`, `ArchiveScreen`으로 화면 단위를 분리
- `styles.css` 단일 파일을 `tokens.css`, `layout.css`, `screens.css`로 분리하고 `index.css`로 진입점 정리
- `core-frontend/ARCHITECTURE.md` 작성, `README.md` 갱신
- 사용되지 않는 옛 `src/styles.css` 제거

검증:
- `npm run build` 통과
- browser에서 시작 화면 / 홈 피드 / 하단 탭 렌더링 확인
- DOM 기준 `ui-demo-user`의 onboarded 홈 상태 확인

판단:
- 이제 프론트는 시연용 프로토타입이면서도 화면/공통 UI/API orchestration의 책임이 분리된 구조를 갖는다.
- 이후 디자인 polish를 더 진행하더라도 공통 요소를 복붙하지 않고 재사용하는 방향을 유지할 수 있다.



## 2026-04-28 18:48:05 KST — PDF reference 레이아웃 비교 기반 깨짐 수정

- 시작/홈/상세/스크랩/아카이브 화면을 PDF app-screens 기준과 브라우저 화면으로 반복 비교했다.
- 폰 베젤/status/browser chrome은 구현 대상에서 제외하고, 베젤 안쪽 앱 화면만 유지했다.
- 시작 화면:
  - 질문 문구를 PDF처럼 2줄 중심 정렬로 조정했다.
  - 관심사 설정/다됐어요 진행 라인, 선택 카드 높이/간격, CTA 위치를 보정했다.
- 홈 화면:
  - 2열 카드 높이를 고정하고 텍스트 clamp를 적용해 행 하단선이 깨지지 않게 했다.
  - 첫 화면 카드 수를 6개로 제한해 단독 카드가 남는 레이아웃을 피했다.
- 상세 화면:
  - 떠 있는 X 닫기 버튼을 제거하고 앱 내부 상단 헤더 + 뒤로 화살표 구조로 바꿨다.
  - 한국어 줄바꿈에 `word-break: keep-all`을 적용하고 제목/본문 크기와 버튼 간격을 조정했다.
- 스크랩/아카이브:
  - 홈의 2열 그리드를 물려받지 않도록 `list-screen`으로 분리했다.
  - 스크랩/아카이브 카드는 1열 full-width 목록형으로 변경했다.
  - archive hero, 월 선택, 날짜칩, 카드 리스트 사이 중복 margin/gap을 줄였다.
- 검증:
  - `npm run typecheck && npm run build` 통과.
  - browser flow: start → home → detail → scraps → archive 통과.
  - forbidden chrome query `.safari-frame,.ios-statusbar,.safari-toolbar,.home-indicator,.phone-frame,.board-rail` false.
  - console warning/error 없음.


## 2026-04-28 19:03:00 KST — PDF 초기 온보딩 플로우 복원

- 시작 화면이 `startDemo`로 바로 홈/피드로 가던 문제를 수정했다.
- `IntroScreen`은 이제 `넓게 볼랭` / `깊게 볼랭` mode 선택과 `다음`만 담당한다.
- `startPreferenceFlow`를 추가해 시작 → 관심사 선택 화면으로 진입하도록 분리했다.
- `restartIntroFlow`를 추가해 온보딩의 `이전`으로 다시 시작 화면으로 돌아갈 수 있게 했다.
- `usePreferenceSelection` 기본 선택값을 비워, 사용자가 실제로 선택해야만 다음 단계로 진행되도록 바꿨다.
- `wide` 규칙: 대분류 3개 이상, 최대 5개.
- `narrow` 규칙: 대분류 1개 선택 후 소분류 1개 이상 다중 선택.
- 온보딩 화면에서 mode segmented toggle을 제거하고, 시작 화면에서 고른 mode 분기만 보여주도록 수정했다.
- `OnboardingScreen` 문구에서 slug(`economy`) 대신 사용자용 라벨(`경제`)이 보이도록 수정했다.
- 브라우저 검증:
  - 시작 → 넓게 → 다음 disabled(0개/2개), enabled(3개) 확인
  - 온보딩 `이전` → 시작 화면 복귀 확인
  - 시작 → 깊게 → 대분류 1개 선택 → `소분류 고르기` 활성화 확인
  - 깊게 2단계에서 소분류 0개면 다음 disabled, 1개 선택 후 enabled 확인
- `npm run typecheck && npm run build` 통과.


## 2026-04-28 19:44:53 KST — 온보딩 완료 화면 + 카카오 로그인 진입 복원

- PDF 상단 중앙 누락 화면을 다시 확인해 `온보딩 완료 (수정 가능)` → `카카오 로그인` 흐름을 구현했다.
- `useViewState`에 `onboarding-complete` 탭을 추가했다.
- 관심사 저장 후 더 이상 바로 뉴스홈으로 가지 않고, `submitPreferences()`에서 저장 성공 후 `onboarding-complete` 화면으로 이동하도록 바꿨다.
- 새 화면 `OnboardingCompleteScreen.tsx`를 추가했다.
  - 앱 내부 라벨은 PDF 기준으로 유지: `Annoying Cap / 26.04.07 / 스크랩 | 아카이브`
  - 본문 문구: `관심있는 분야를 최소 3개 이상 선택해서 / 하루에 한번씩 요약해서 받아보세요`
  - 진행 상태: `3번째 / 완료!`
  - 칩 요약: `Wide 유저` + `경제 · 정치 · 연예` 형태
  - CTA: `카카오 로그인하고 매일 블록 받아보기`
- 완료 화면의 칩을 누르면 다시 관심사 편집 화면으로 돌아가도록 연결했다.
- 완료 화면의 CTA는 `beginKakaoStart()`를 호출해 카카오 인증 팝업을 연다.
- 온보딩/온보딩 완료 단계에서는 상단 `TopBar`를 숨기도록 정리했다.
- 브라우저 검증:
  - wide 선택 → 3개 선택 → `다음` → `온보딩 완료` 화면 진입 확인
  - 완료 화면에 요약 칩 2개와 카카오 CTA 노출 확인
  - `Wide 유저` 칩 클릭 시 관심사 편집 화면 복귀 확인
  - 카카오 CTA 클릭 시 `window.open` 1회 호출 확인
- `npm run typecheck && npm run build` 통과.

## 2026-04-28 21:07:05 KST
- PDF reference 기준으로 wide/narrow 온보딩 화면을 추가 보정했다.
- wide 화면: 헤더/진행바/2열 카드형 대분류 선택/하단 CTA 구조를 PDF 03-wide-categories-inner 기준으로 재정렬했다.
- narrow 1단계: 대분류 1개 선택 화면으로 정리하고 중복 액션을 제거했다. 하단 primary CTA는 소분류 단계 진입으로 동작한다.
- narrow 2단계: 소분류 카드 선택 + 대분류 다시 고르기 + 이전/다음 구조로 정리했다.
- 브라우저 vision 기준 wide/narrow 모두 큰 레이아웃 깨짐은 없고 미세 차이 수준으로 확인했다.
- 검증: npm run typecheck && npm run build 통과, browser console error 0.

