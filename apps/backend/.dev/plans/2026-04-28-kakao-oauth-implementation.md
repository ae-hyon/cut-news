# Annoying Cap Kakao OAuth Implementation Plan

> For Hermes: Use strict TDD for every production code change in this plan.

작성 시각: 2026-04-28 08:25:50 KST

목표:
- placeholder 상태인 `/v1/auth/session`을 실제 Kakao OAuth 흐름과 내부 사용자 매핑을 수용할 수 있는 백엔드 경계로 확장한다.

아키텍처:
- 외부 provider(Kakao)와 내부 user preference/feed/scrap 경계를 분리한다.
- presentation 계층은 OAuth start/callback/session contract를 제공하고, application 계층은 provider subject -> internal user_id 매핑과 상태 판정을 담당한다.
- 실제 Kakao 앱 시크릿이 없어도 로컬에서 검증 가능한 수준까지 구현하고, 외부 HTTP 교환은 주입 가능한 client interface 뒤로 숨긴다.

기술 스택:
- FastAPI
- Pydantic v2
- SQLAlchemy
- Alembic
- pytest / TestClient

관련 파일:
- `app/presentation/api/routes/auth.py`
- `app/presentation/schemas.py`
- `app/presentation/api/dependencies.py`
- `app/application/services/user_service.py`
- `app/domain/entities.py`
- `app/domain/repositories.py`
- `app/infrastructure/models.py`
- `app/infrastructure/repositories.py`
- `app/common/config.py`
- `alembic/versions/`
- `tests/test_auth_routes.py`
- `README.md`
- `.dev/PRD.md`
- `.dev/current-status.md`
- `.dev/progress-log.md`

---

## Task 1: Kakao auth contract RED 테스트 추가

목표:
- start/callback/session에 필요한 최소 API 계약을 failing test로 고정한다.

파일:
- Modify: `tests/test_auth_routes.py`
- Optionally create: `tests/test_auth_service.py`

Step 1: failing test 작성
- `GET /v1/auth/kakao/start`가 `authorization_url`, `state`, `provider`를 반환해야 한다.
- `GET /v1/auth/kakao/callback?code=...&state=...`가 내부 `user_id`, `provider_subject`, `session_state=authenticated`를 반환해야 한다.
- `GET /v1/auth/session?provider=kakao&provider_subject=...`가 매핑된 사용자를 authenticated로 돌려줘야 한다.

Step 2: RED 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: FAIL

Step 3: 최소 구현
- production code는 아직 쓰지 말고, 테스트가 정확히 어떤 contract를 요구하는지 확정한다.

Step 4: 재검토
- 응답 필드가 프론트 시작점으로 충분한지 확인한다.

## Task 2: Domain model/repository 계약 추가

목표:
- 외부 provider identity와 내부 user mapping을 저장할 도메인 계약을 만든다.

파일:
- Modify: `app/domain/entities.py`
- Modify: `app/domain/repositories.py`
- Modify: `tests/test_auth_routes.py` 또는 `tests/test_auth_service.py`

Step 1: failing test 작성
- auth service가 mapping repository 없이는 authenticated 세션을 만들 수 없음을 테스트로 고정한다.

Step 2: RED 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: FAIL

Step 3: 최소 구현
- `ExternalIdentity` 또는 동등한 Pydantic entity 추가
- repository protocol 추가 (`get_by_provider_subject`, `save`)

Step 4: GREEN 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: 해당 import/path 에러가 사라지고 다음 단계 실패로 이동

## Task 3: SQLAlchemy model/repository + Alembic migration 추가

목표:
- `provider + provider_subject -> user_id` 매핑을 DB에 저장한다.

파일:
- Modify: `app/infrastructure/models.py`
- Modify: `app/infrastructure/repositories.py`
- Create: `alembic/versions/0002_external_identities.py`

Step 1: failing test 작성
- callback 처리 후 mapping 조회가 가능해야 한다.

Step 2: RED 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: FAIL

Step 3: 최소 구현
- `external_identities` 테이블 추가
- unique(provider, provider_subject), unique(provider, user_id) 정도의 최소 제약 적용
- SQLAlchemy repository 구현

Step 4: GREEN 검증
Run: `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')`
Expected: PASS

## Task 4: OAuth client/service 경계 구현

목표:
- Kakao authorization URL 생성과 callback code 교환 결과를 application service 뒤로 숨긴다.

파일:
- Create: `app/application/services/auth_service.py`
- Create or Modify: `app/application/clients/` 관련 파일
- Modify: `app/common/config.py`
- Modify: `app/presentation/api/dependencies.py`

Step 1: failing test 작성
- auth route가 provider-specific 로직을 직접 갖지 않고 service를 통해 start/callback/session을 처리함을 테스트한다.

Step 2: RED 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: FAIL

Step 3: 최소 구현
- `build_authorization_url()`
- `exchange_code_for_identity()`
- `resolve_session()`
- 환경변수: `KAKAO_REST_API_KEY`, `KAKAO_REDIRECT_URI`, `KAKAO_CLIENT_SECRET`(optional), `KAKAO_AUTHORIZE_URL`, `KAKAO_TOKEN_URL`, `KAKAO_USERINFO_URL`
- 외부 HTTP는 injectable client로 분리

Step 4: GREEN 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: PASS

## Task 5: Auth routes/session schema 확장

목표:
- 프론트가 바로 쓸 수 있는 start/callback/session contract를 완성한다.

파일:
- Modify: `app/presentation/api/routes/auth.py`
- Modify: `app/presentation/schemas.py`

Step 1: failing test 작성
- `provider`, `authorization_url`, `state`, `provider_subject` 등 응답 필드 검증

Step 2: RED 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: FAIL

Step 3: 최소 구현
- `GET /v1/auth/kakao/start`
- `GET /v1/auth/kakao/callback`
- 기존 `/v1/auth/session`은 `user_id` fallback + `provider/provider_subject` lookup 둘 다 지원

Step 4: GREEN 검증
Run: `PYTHONPATH=. python3.11 -m pytest tests/test_auth_routes.py -q`
Expected: PASS

## Task 6: 문서/런타임 검증

목표:
- README와 `.dev`가 실제 구현 상태를 반영하게 맞춘다.

파일:
- Modify: `README.md`
- Modify: `.dev/PRD.md`
- Modify: `.dev/current-status.md`
- Modify: `.dev/progress-log.md`

Step 1: 테스트/컴파일
Run:
- `PYTHONPATH=. python3.11 -m pytest tests -q`
- `python3.11 -m py_compile $(find app alembic tests -name '*.py' | tr '\n' ' ')`

Step 2: 필요 시 런타임 smoke
Run:
- `PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8011`
- `curl http://127.0.0.1:8011/v1/auth/kakao/start`

Step 3: 문서 업데이트
- README에는 실행/환경변수/엔드포인트만
- `.dev`에는 상태/제약/다음 작업 기록

---

## 구현 범위 메모
- 이번 단계에서는 실제 카카오 운영 앱과의 end-to-end 성공보다, 백엔드 경계와 내부 매핑 저장소를 먼저 완성한다.
- 실제 외부 HTTP 호출은 dependency injection 뒤로 숨겨 테스트에서 stub 가능해야 한다.
- 세션 토큰 발급까지는 아직 범위를 넓히지 않는다. 현재 단계는 provider subject 매핑과 authenticated 상태 판정까지다.

## 완료 정의
- `/v1/auth/kakao/start` contract 존재
- `/v1/auth/kakao/callback` contract 존재
- `/v1/auth/session`이 provider subject 기준 authenticated 세션을 반환 가능
- `external_identities` 저장소와 migration 존재
- pytest/compile 통과
- README/.dev 동기화 완료
