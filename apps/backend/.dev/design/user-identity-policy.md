# User Identity Policy

최종 갱신: 2026-04-28 02:13:14 KST

## 목적
현재 `user_id`가 어떤 의미로 쓰이고 있는지, 그리고 추후 Kakao 로그인 도입 시 어떤 외부 식별자로 치환/매핑할지 정리한다.

## 현재 정책
- 현재 backend의 사용자 식별자는 path/query 수준의 `user_id: str`이다.
- seed 기준 대표 사용자는 `demo-user`다.
- `user_id`는 현재 보안적으로 검증된 subject가 아니라 로컬 데모/개발 식별자다.
- `UserPreferenceService.get_preferences(user_id)`는 레코드가 없더라도 default preference를 만들어 반환할 수 있다.
- 실제 persisted 상태는 `PUT /v1/users/{user_id}/preferences` 이후 확정된다.

## 현재 용어 고정
- anonymous user:
  - `user_id`가 없고 서버가 사용자를 특정하지 못하는 상태
- onboarded user:
  - `user_id`가 있고 `onboarding_completed=true`인 상태
  - 현재 backend의 실질적인 홈 진입 가능 사용자
- authenticated user:
  - 추후 외부 인증 공급자(subject)가 검증된 상태
  - 현재는 reserved 상태

## 현재 저장되는 최소 사용자 필드
현재 실제 persistence 관점 최소 필드:
- `user_id: str`
- `mode: wide | narrow`
- `onboarding_completed: bool`
- `primary_categories: list[str]`
- `subcategories: list[str]`

현재 DB 스키마상 사용자 프로필 전용 필드는 `user_preferences`와 연결 테이블에 분산되어 있다.

## Kakao 로그인 도입 시 목표 매핑
추후 권장 방향:
- 내부 canonical user id는 유지하거나 별도 `user_id`/`account_id`로 분리
- 외부 provider identity는 별도 필드로 저장
  - `auth_provider='kakao'`
  - `provider_subject=<kakao user id 또는 subject>`
- 앱 API의 path `user_id`는 점진적으로 내부 canonical id로 사용
- 외부 provider subject는 직접 API path에 노출하지 않는 편이 안전함

권장 매핑 테이블 초안:
- internal_user_id
- auth_provider
- provider_subject
- created_at
- updated_at
- last_login_at
- onboarding_completed_snapshot(optional)

## 왜 지금은 local user id를 유지하는가
- 현재 프론트/백엔드 흐름은 온보딩, 피드, 스크랩, 아카이브를 먼저 검증하는 단계다.
- 실제 OAuth를 먼저 강제하면 제품 플로우 검증보다 인증 인프라 구현이 선행된다.
- 따라서 현재는 `demo-user` 같은 로컬 식별자를 유지하되, `/v1/auth/session` 응답 계약에 future-ready 필드(`auth_provider`, `provider_subject`, `authenticated`)를 미리 포함한다.

## API 경계 원칙
- 현재 사용자 관련 자원은 모두 `user_id` path를 받는다.
- 현재 `user_id`는 trusted auth claim이 아니라 개발용 식별자이므로, 운영 전환 전에는 인증 미들웨어 또는 세션 검증 계층이 추가되어야 한다.
- 추후 Kakao 연동 시에도 기존 자원 path를 전면 변경하지 않고, 인증 계층에서 internal user id를 resolve 하도록 설계하는 것이 목표다.

## 결론
- 지금의 `user_id`는 demo/local identity다.
- 이 값을 바로 Kakao subject로 바꾸는 것보다, 추후 provider mapping 계층을 추가하는 쪽이 API 안정성이 높다.
- 현재 백엔드의 완료 기준은 사용자 도메인과 자원 흐름을 먼저 고정하고, 인증은 reserved boundary로 수용하는 것이다.
