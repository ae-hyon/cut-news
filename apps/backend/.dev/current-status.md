- After saving onboarding preferences, the app now enters a dedicated PDF-matching `onboarding-complete` screen instead of jumping straight to the feed; that screen supports editing the chosen interests and starting Kakao login from the CTA.
- Initial onboarding flow now matches the PDF branch logic: start screen only chooses `wide` vs `narrow`, then enters onboarding; `wide` requires 3-5 primary categories, `narrow` requires 1 primary category plus 1+ subcategories, and onboarding can return to the intro screen via `이전`.
# Annoying Cap Core Backend Current Status

최종 갱신: 2026-04-28 18:09:19 KST

## 현재 상태 요약
- FastAPI + DDD + layered architecture 기반 백엔드가 동작 중
- local Postgres + Docker Compose + Alembic migration 적용 완료
- `../news_summurizer` 연동 `/v1/summaries` 제공 중
- summary gateway가 API schema -> summarizer schema typed boundary를 거치도록 정리됨
- `/v1/auth/session`, `/v1/auth/kakao/start`, `/v1/auth/kakao/callback`, `/v1/auth/refresh`, `/v1/auth/logout` 경계가 추가됨
- callback은 redirect 없이 session JSON과 `HttpOnly` access/refresh cookie를 반환함
- Kakao OAuth state는 서명된 토큰으로 발급/검증함
- `external_identities` 저장소로 Kakao `provider_subject -> internal user_id` 매핑 가능
- `refresh_sessions` 저장소로 refresh token rotation과 logout revoke를 처리함
- refresh token은 원문이 아니라 SHA-256 hash로 저장하고 `issued_at` / `last_used_at` / `revoked_at` 메타데이터를 보관함
- 실제 uvicorn + curl 검증까지 완료된 상태
- `../core-frontend`에 Flow PDF 톤을 반영한 React + Vite 프로토타입을 추가했고 browser로 온보딩/홈/상세/스크랩/아카이브를 검증함
- 프론트 polish로 Kakao 시작 CTA, narrow 2단계 온보딩 UX, 하단 탭 히트박스/버튼 간격 개선을 반영했고, React 코드는 TSX/TypeScript 기준으로 전환함; frontend hook/service/view-state 분리로 auth/session, content feed, archive, preference 선택 상태와 화면 전환 reducer를 재사용 가능하게 정리함
- `../core-frontend/src`를 `App / hooks / lib / components / styles` 구조로 재정리했고, `NewsCard`/`BottomNav`/`SectionHeader` 등을 재사용 컴포넌트로 분리함
- 프론트는 PDF의 폰 베젤/status/browser bar를 구현하지 않고, 베젤 안쪽 앱 화면만 393px 중앙 캔버스로 렌더링하도록 전환함
- 사용자 화면에서 `WEIGHT`, `Block`, debug/session 상태 같은 내부 용어와 Safari/phone chrome, 반사광/gradient를 제거하고 PDF 내부 앱 화면 기준으로 재정렬함

## 현재 구현 범위
- 카테고리/서브카테고리 조회
- Kakao auth start/callback/session/refresh/logout contract
- JWT access token + DB-backed refresh session
- signed OAuth state issue/verify
- 분리된 auth application domain (`app/application/auth/*`)
- refresh token hash 저장 + session metadata (`issued_at`, `last_used_at`, `revoked_at`)
- 사용자 선호 조회/수정
- onboarding 완료 validation (wide/narrow 규칙 + 중복 금지)
- 사용자 피드 조회
- Flow PDF 기준 피드 가중치/정렬 정책 (wide 순서 보존, narrow focus block, article score 내림차순)
- 기사 상세 조회
- 스크랩 추가/삭제/조회
- 월/일 아카이브 조회
- 뉴스 요약 생성

## 확인된 운영 기준
- 공식 실행 Python: `python3.11`
- 앱 이름: `Annoying Cap Core Backend`
- API Prefix: `/v1`
- DB: local Postgres via Docker Compose
- migration: Alembic
- sibling summarizer dir: `../news_summurizer`

## 현재 검증 상태
- `PYTHONPATH=. python3.11 -m pytest tests -q` 통과
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')` 통과
- `python3.11 -m alembic upgrade head` 통과
- 실제 uvicorn 기동 확인 (`127.0.0.1:8013`)
- `GET /health` 정상
- `GET /v1/auth/kakao/start` 정상
- `GET /v1/auth/session` anonymous 정상
- `GET /v1/auth/session?user_id=demo-user` onboarded 정상
- `GET /v1/auth/session?provider=kakao&provider_subject=runtime-kakao-001` authenticated 정상
- JWT access cookie 기반 `GET /v1/auth/session` authenticated 정상
- `POST /v1/auth/refresh` cookie rotation 정상
- `POST /v1/auth/logout` cookie clear 정상
- `POST /v1/summaries` 실제 요약 응답 정상
- callback JSON 응답 + `HttpOnly` cookie는 TestClient로 검증 완료
- DB-backed `AuthService.complete_kakao_callback()` / `resolve_session()` / `refresh_session()` 검증 완료
- `PUT /v1/users/{user_id}/preferences`의 wide/narrow validation 및 onboarding 완료 전이 검증 완료
- `FeedService.get_feed()`의 block weight/순서/article 정렬 규칙 검증 완료
- `../core-frontend`에서 `ui-demo-user` 기준 anonymous -> onboarded -> 홈 피드 -> 기사 상세 -> 스크랩 -> 아카이브 표시 브라우저 검증 완료
- 온보딩 탭 active 상태와 Kakao CTA 존재, narrow 2단계 온보딩 코드/빌드 반영 확인 완료
- Kakao 시작 UX는 popup open, focus/visibility 복귀 후 `/v1/auth/session` 자동 재확인, 수동 `로그인 완료 확인` 실패 안내까지 browser stub으로 검증 완료
- hook 분리 후 `npm run typecheck && npm run build` 통과, browser에서 홈/상세/아카이브/관심사 플로우와 React key warning 제거 확인 완료
- view-state reducer 전환 후 `npm run build` 통과, browser에서 홈 -> 상세 -> 홈 -> 스크랩 -> 아카이브 -> 관심사 플로우와 nav hide/show 규칙 확인 완료
- PDF 앱 내부 화면 재정렬 후 `npm run typecheck && npm run build` 통과, browser에서 393px 앱 캔버스와 phone/browser chrome 미노출 확인 완료

## 이미 반영된 주요 결정
- Annoying Cap 브랜딩 사용
- dataclass보다 Pydantic 중심 일관성 유지
- local DB + Docker Compose 사용
- startup migration + seed 사용
- 요약은 라이브러리 import 방식으로만 연동
- 사용자-facing 조회 API는 저장된 summary를 읽고, `/v1/summaries`는 생성/검증 경계로 분리
- auth는 `user_id` fallback, Kakao `provider_subject` lookup, JWT access cookie lookup을 함께 지원
- Kakao callback은 frontend 비의존 API 응답 + `HttpOnly` access/refresh cookie 설정 방식으로 정리
- Kakao OAuth state는 JWT 서명 토큰으로 발급하고 callback에서 만료/위변조를 검증
- refresh token은 `refresh_sessions` 저장소에 SHA-256 hash로 보관하고 rotation / revoke를 지원
- `issued_at` / `last_used_at` / `revoked_at` 메타데이터를 세션 추적용으로 유지
- auth application 영역은 `app/application/auth/` 하위로 분리하고, `services/auth_service.py`는 orchestrator façade만 유지
- Kakao 외부 HTTP 교환은 `DefaultKakaoOAuthClient` 뒤로 숨기고 repository로 내부 매핑을 고정

## 후순위 고도화 백로그
1. 현재 단순 가중치(1.0/0.85/0.70...)를 실제 사용자 반응/스크랩 신호까지 반영하는 정책으로 확장한다.
2. summary 생성 endpoint를 ingest/backoffice 경로와 어떻게 연결할지 운영 플로우 확정
3. Kakao token/userinfo 실패 taxonomy를 더 세분화하고 사용자-facing 에러 정책을 정리한다.
4. refresh session의 기기/클라이언트 fingerprint 정책이 필요하면 metadata를 더 확장한다.
5. 사용자 행동 로그를 활용한 개인화 실험 정책을 별도 문서/테이블로 분리한다.

## 관련 문서
- `.dev/PRD.md`
- `.dev/current-status.md`
- `.dev/progress-log.md`
- `.dev/plans/2026-04-28-auth-and-summary-flow.md`
- `.dev/plans/2026-04-28-kakao-oauth-implementation.md`
- `.dev/design/auth-state-machine.md`
- `.dev/design/user-identity-policy.md`
- `.dev/design/summary-lifecycle.md`
- `.dev/design/summary-sequence.md`
- `README.md`
- `../어노잉캡-Flow.pdf`
- `../news_summurizer/docs/current-status.md`

## 2026-04-28 21:07:05 KST
- PDF reference 기준으로 wide/narrow 온보딩 화면을 추가 보정했다.
- wide 화면: 헤더/진행바/2열 카드형 대분류 선택/하단 CTA 구조를 PDF 03-wide-categories-inner 기준으로 재정렬했다.
- narrow 1단계: 대분류 1개 선택 화면으로 정리하고 중복 액션을 제거했다. 하단 primary CTA는 소분류 단계 진입으로 동작한다.
- narrow 2단계: 소분류 카드 선택 + 대분류 다시 고르기 + 이전/다음 구조로 정리했다.
- 브라우저 vision 기준 wide/narrow 모두 큰 레이아웃 깨짐은 없고 미세 차이 수준으로 확인했다.
- 검증: npm run typecheck && npm run build 통과, browser console error 0.

