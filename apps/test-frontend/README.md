# Annoying Cap Core Frontend

React + Vite + TypeScript 기반의 모바일/PWA 지향 프론트엔드 프로토타입입니다.

목적
- `어노잉캡-Flow.pdf`의 톤과 핵심 화면 구조를 430px 고정 모바일 캔버스에 맞춰 재현
- `core-backend` API에 실제로 붙여서 온보딩/세션/피드/상세/스크랩 흐름을 브라우저에서 검증
- 스크랩은 현재 관심 분야 필터와 별개로 유지되는 개인 저장 목록으로 취급
- 백엔드는 API-only, 프론트는 session/resource 상태 기반으로 화면 전환


PWA/화면 기준
- 데스크톱 웹에서는 430px 폭의 중앙 고정 모바일 앱 캔버스로 표시합니다.
- 430px 이하 실제 모바일/PWA에서는 100vw로 꽉 차게 표시합니다.
- `public/manifest.webmanifest`, `public/icons/icon.svg`, mobile meta/theme-color를 포함합니다.
- `WEIGHT`, `Block`, debug/session 같은 내부 용어는 기본 사용자 화면에 노출하지 않습니다.
- 개발 확인용 상태 패널은 `http://127.0.0.1:5173?debug=1`에서만 접을 수 있는 debug 패널로 표시합니다.

현재 범위
- 시작 화면
- 온보딩 화면 (wide / narrow 2단계)
- 홈 피드
- 기사 상세
- 스크랩
- Kakao 시작 CTA + popup/focus 복귀 후 session 재확인 UX

실행
- 백엔드
  - `cd ../core-backend`
  - `DATABASE_URL=sqlite:///./dev-ui.db PYTHONPATH=. python3.11 -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
- 프론트
  - `npm install`
  - `npm run dev`
- 타입/빌드 검증
  - `npm run typecheck`
  - `npm run build`
- 접속
  - `http://127.0.0.1:5173`

파일 구조
- `src/main.tsx`
  - 진입점. `App` 렌더와 전역 스타일 import만 담당.
- `src/App.tsx`
  - 화면 조립 전용. 비즈니스 로직 최소화.
- `src/hooks/usePrototypeApp.ts`
  - domain hook + view-state orchestration 조립.
- `src/hooks/useViewState.ts`
  - tab/detail 화면 전환 reducer.
- `src/hooks/useAuthSession.ts`
  - health/session/Kakao bootstrap 상태.
- `src/hooks/useContentFeed.ts`
  - feed/detail/scrap 상태.
- `src/hooks/usePreferenceSelection.ts`
  - wide/narrow 선택 상태, subcategory map, preference payload 변환.
- `src/services/backendApi.ts`
  - backend endpoint별 typed service 함수.
- `src/lib/api.ts`
  - fetch wrapper.
- `src/lib/constants.ts`
  - 데모 사용자, 카드 tone, 카테고리 한글 라벨 상수.
- `src/lib/types.ts`
  - 백엔드 API 응답과 프론트 도메인 타입.
- `src/components/layout/*`
  - `AppShell`, `TopBar`. 웹에서는 중앙 430px 앱 캔버스, 실제 모바일에서는 100vw로 동작.
- `src/components/navigation/*`
  - `BottomNav`.
- `src/components/common/*`
  - 여러 화면에서 재사용되는 `NewsCard`, `SectionHeader`, `DevPanel` (`?debug=1`에서만 표시).
- `src/components/screens/*`
  - `IntroScreen`, `OnboardingScreen`, `HomeScreen`, `DetailScreen`, `ScrapsScreen`.
- `src/styles/*`
  - `tokens.css`, `layout.css`, `screens.css`, `index.css`.

재사용 원칙
1. 화면 전용 조합은 `screens/`에 둔다.
2. 둘 이상 화면에서 쓰는 UI는 `common/`, `layout/`, `navigation/`으로 올린다.
3. API 호출은 컴포넌트 안에서 직접 하지 않고 `services/backendApi.ts` 또는 hook을 통한다.
4. `App.tsx`는 상태를 만들지 않고, hook이 반환한 props를 화면 컴포넌트에 전달만 한다.
5. 카드/헤더/탭처럼 반복되는 UI는 공통 props 기반으로 재사용한다.

현재 확인된 재사용 예
- `NewsCard`
  - 홈 피드, 스크랩 화면에서 공통 사용
- `SectionHeader`
  - 피드 블록 헤더 공통 사용
- `BottomNav`
  - 홈/온보딩/스크랩 전환 공통 사용

주의
- Kakao 시작 UX는 popup/focus 복귀 후 session 재확인까지 구현되어 있습니다. 단, 실제 Kakao 계정 E2E는 로컬 브라우저 자동화에서 완료 검증하지 않았습니다.
- 브라우저 테스트는 `ui-demo-user` 흐름을 우선 사용합니다.
- 후순위 고도화 항목(개인화, 행동 신호, 운영 플로우)은 `core-backend/.dev/*` 문서에 백로그로 남겨두었습니다.
- 구조/계층 설명은 `ARCHITECTURE.md`를 참고합니다.
