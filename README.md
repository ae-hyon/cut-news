# Cut News

뉴스 수집 및 분석 플랫폼

## 기술 스택

### Backend & Crawler
- Python 3.12+
- FastAPI
- uv (패키지 관리)
- ruff (린팅/포맷팅)
- mypy (타입 체크)
- pytest (테스트)

### Frontend
- Next.js 15
- React 19
- TypeScript
- pnpm

## 프로젝트 구조

```
cut-news/
├── apps/
│   ├── backend/      # FastAPI 백엔드 API (port 8000)
│   ├── crawler/      # 크롤러 서비스 (port 8001)
│   └── frontend/     # Next.js 프론트엔드 (port 3000)
├── packages/         # 공유 코드 (추후)
├── scripts/          # 개발 스크립트
├── Makefile          # 개발 명령어
└── pyproject.toml    # Python workspace 설정
```

## 시작하기

### 필수 요구사항
- Python 3.12+
- Node.js 20+
- uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- pnpm (`npm install -g pnpm`)

### 설치

```bash
# 전체 설치
make install

# 또는 개별 설치
make install-backend
make install-crawler
make install-frontend
```

## 개발

```bash
# 백엔드 서버 (http://localhost:8000)
make dev-backend

# 크롤러 서버 (http://localhost:8001)
make dev-crawler

# 프론트엔드 (http://localhost:3000)
make dev-frontend
```

## 코드 품질

```bash
# 린트
make lint

# 포맷팅 (Python)
make format

# 타입 체크
make type-check

# 테스트
make test
```

## API 문서

- Backend: http://localhost:8000/docs
- Crawler: http://localhost:8001/docs
