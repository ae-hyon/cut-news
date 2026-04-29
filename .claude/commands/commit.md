# Git Commit

변경사항을 분석하고 Conventional Commits 한국어 커밋 메시지를 작성하여 커밋을 생성한다.

## 커밋 메시지 형식

```
<type>(<scope>): <한국어 설명>
```

### Type

| type | 용도 |
|------|------|
| feat | 새로운 기능 추가 |
| fix | 버그 수정 |
| refactor | 리팩토링 (기능 변경 없이 코드 구조 개선) |
| style | 코드 포맷팅, 세미콜론 누락 등 (로직 변경 없음) |
| docs | 문서 수정 |
| test | 테스트 코드 추가/수정 |
| chore | 빌드 설정, 패키지 매니저, CI 등 보조 작업 |
| perf | 성능 개선 |

### Scope (모노레포 자동 판별)

- `apps/frontend/` → `frontend`
- `apps/backend/` → `backend`
- `apps/crawler/` → `crawler`
- 루트 파일 (`package.json`, `Makefile` 등) → `root`
- `scripts/` → `scripts`
- 여러 앱에 걸친 변경 → 변경이 가장 많은 앱을 scope로 사용

### 커밋 메시지 규칙

- 제목 50자 이내, 간결하게
- "무엇을" 보다 "왜"에 초점
- 변경이 많으면 본문 추가 (제목과 빈 줄로 구분)

### 예시

```
feat(frontend): 뉴스 카드 컴포넌트 추가
fix(backend): 크롤링 데이터 파싱 오류 수정
chore(root): pnpm workspace 설정 업데이트
```

## 실행 절차

1. `git status`와 `git diff`를 병렬로 실행하여 변경 내용 파악
2. `git log --oneline -5`로 최근 커밋 스타일 참고
3. 변경 파일 경로 분석 → scope 자동 판별
4. 변경 내용 분석 → type 자동 판별
5. 논리적으로 분리 가능한 변경이면 여러 커밋으로 나눔
6. 한국어 커밋 메시지 작성
7. 파일 개별 지정하여 staging (`git add` — `.env`, 인증 정보 등 민감 파일 제외)
8. 커밋 생성 (HEREDOC 사용, Co-Authored-By 포함)
9. `git status`로 결과 확인

## 주의사항

- `.env`, credentials, 시크릿 파일은 절대 커밋하지 않는다
- `git add .`이나 `git add -A` 대신 파일을 개별 지정한다
- pre-commit hook 실패 시 문제를 수정하고 새 커밋을 만든다 (amend 하지 않음)
- 사용자가 명시적으로 요청하지 않은 한 push하지 않는다
