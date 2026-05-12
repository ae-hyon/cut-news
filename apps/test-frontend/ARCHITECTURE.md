# Core Frontend Architecture

최종 갱신: 2026-04-28 17:30:45 KST

## 목표
이 프론트는 `어노잉캡-Flow.pdf`를 빠르게 시연 가능한 React + TypeScript 프로토타입으로 옮기되,
다음 조건을 지키도록 구성한다.

- 단일 대형 파일에 로직/레이아웃/스타일을 몰아넣지 않는다.
- 공통 UI는 화면별로 복붙하지 않고 재사용한다.
- API 호출은 화면 컴포넌트에 흩뿌리지 않고 hook/lib 계층으로 모은다.
- `App.tsx`는 조립만 하고, 상태 orchestration은 hook으로 뺀다.

## 디렉터리 구조

```text
src/
  main.tsx                     # 진입점
  App.tsx                      # 화면 조립 전용
  lib/
    api.ts                     # fetch wrapper
    constants.ts               # demo/config 상수
    types.ts                   # API/domain 타입
  hooks/
    usePrototypeApp.ts         # domain hook + view-state orchestration 조립
    useViewState.ts            # tab/detail 화면 전환 reducer
    useAuthSession.ts          # health/session/Kakao bootstrap 상태
    useContentFeed.ts          # feed/detail/scrap 상태
    usePreferenceSelection.ts  # wide/narrow 선택 상태 + payload 변환
  services/
    backendApi.ts              # typed backend endpoint 함수
  components/
    layout/
      AppShell.tsx             # 중앙 430px 앱 캔버스 + PWA shell
      TopBar.tsx               # 상단 브랜드/화면 제목
    navigation/
      BottomNav.tsx            # 하단 탭 네비게이션
    common/
      NewsCard.tsx             # 홈/스크랩 공통 카드
      SectionHeader.tsx        # 피드 블록 헤더 공통
    screens/
      IntroScreen.tsx          # 시작 화면
      OnboardingScreen.tsx     # wide/narrow 온보딩
      HomeScreen.tsx           # 홈 피드
      DetailScreen.tsx         # 기사 상세
      ScrapsScreen.tsx         # 스크랩 목록
  styles/
    tokens.css                 # 색상/토큰/전역 기초
    layout.css                 # 앱/프레임/네비 구조
    screens.css                # 화면/카드/온보딩 세부 스타일
    index.css                  # 스타일 진입점
```

## 계층 규칙

### 1. `lib/`
- 순수 유틸과 상수만 둔다.
- React state를 알면 안 된다.
- 예: `api.ts`, `constants.ts`

### 2. `hooks/`
- 화면 상태 전이와 로컬 UI 선택 상태를 관리한다.
- `usePrototypeApp.ts`는 app-level orchestration 조립만 맡는다.
- `useViewState.ts`는 tab/detail 화면 전환 reducer를 맡는다.
- `useAuthSession.ts`는 health/session/Kakao bootstrap, popup 시작, focus/visibility 복귀 후 session 재확인 상태를 맡는다.
- `useContentFeed.ts`는 feed/detail/scrap 상태와 content refresh를 맡는다.
- `usePreferenceSelection.ts`는 wide/narrow 선택 상태, subcategory map, preference payload 변환을 맡는다.

### 3. `services/`
- backend endpoint별 typed 함수만 둔다.
- React state를 알면 안 된다.
- 화면/hook은 raw path 문자열을 직접 만들지 말고 가능하면 `services/backendApi.ts`를 사용한다.

### 4. `components/layout/`
- 앱 전체 프레임에 가까운 UI.
- 구체 화면 데이터보다 배치/레이아웃 역할이 크다.

### 5. `components/navigation/`
- 화면 전환 UI만 둔다.
- 라우팅/탭 전환 계약을 표현하지만, 데이터 fetch는 하지 않는다.

### 6. `components/common/`
- 둘 이상의 screen에서 재사용되는 UI.
- 현재 핵심 공통 컴포넌트:
  - `NewsCard`
  - `SectionHeader`
  - `DevPanel` (`?debug=1` only)

### 7. `components/screens/`
- 화면 단위 조합 계층.
- 같은 화면 안에서만 필요한 배치 로직은 여기 둔다.
- 가능하면 API 호출은 직접 하지 않고 props로 받은 action을 호출한다.

## 재사용 원칙

### 공통 카드 재사용
`NewsCard`는 다음 화면에서 재사용한다.
- HomeScreen
- ScrapsScreen

이렇게 해서 제목/요약/스크랩 버튼/상세 버튼 구조를 한 군데에서 유지한다.

### 공통 섹션 헤더 재사용
`SectionHeader`는 피드 섹션 제목/index 표현을 공통화한다. 내부 weight 값은 사용자 화면에 노출하지 않는다.

### 공통 프레임 재사용
`AppShell`, `TopBar`, `BottomNav`는 화면 종류와 무관하게 재사용한다. 데스크톱에서는 430px 중앙 고정, 모바일에서는 100vw를 유지한다.

## 앞으로도 지킬 기준
1. 새 화면이 생겨도 `App.tsx`에 JSX를 길게 늘어놓지 말고 `screens/` 아래로 뺀다.
2. 같은 마크업 패턴이 2번 이상 나오면 `common/` 컴포넌트로 올린다.
3. fetch 로직을 screen 안에서 직접 만들지 않는다. 먼저 hook 또는 `lib/api`에 둘 수 있는지 본다.
4. 스타일도 가능하면 토큰 / 레이아웃 / 화면 계층을 유지한다.
5. PDF 완성도 polish를 하더라도 구조는 더 평평하게 만들지 말고, 공통성과 조합 계층을 유지한다.

## 현재 남은 구조적 개선 후보
- Kakao callback 완료 후 popup/focus 기반 session 재확인 UX는 구현됨; 실제 Kakao 계정 E2E는 별도 수동 검증 필요
- 실제 모바일/PWA 설치 검증 필요

## TypeScript 기준
- 모든 React 컴포넌트는 `.tsx`로 작성한다.
- 순수 로직/API/상수/타입은 `.ts`로 작성한다.
- `npm run typecheck`가 통과하지 않으면 완료로 보지 않는다.
- 백엔드 응답 형태는 `src/lib/types.ts`에 먼저 반영하고, 컴포넌트 props는 그 타입을 재사용한다.
