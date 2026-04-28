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
│   ├── backend/       # FastAPI 백엔드 API (port 8000)
│   ├── crawler/       # 크롤러 서비스 (port 8001)
│   ├── frontend/      # Next.js 프론트엔드 (port 3000)
│   ├── summarizer/    # 뉴스 요약 파이프라인/라이브러리
│   └── test-frontend/ # 백엔드 API 연동 검증용 Vite 프론트엔드
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

## 데이터 파이프라인

자체 뉴스 홈 데이터는 다음 계약으로 이어집니다.

1. `apps/crawler`
   - 다른 팀원이 작업한 crawler가 기사 원문을 수집합니다.
   - backend/summarizer와 직접 맞물리는 저장 포맷은 `apps/crawler/src/crawler/pipeline.py`의 `save_raw_articles()`가 보장합니다.
   - 출력: `apps/summarizer/data/raw/001.txt` 형태
2. `apps/summarizer`
   - `data/raw/*.txt`를 `data/json/*.json`, `data/summarized/*.json`, `data/category_map.json`으로 변환/요약합니다.
   - 실행: `make pipeline-summarizer`
3. `apps/backend`
   - startup seed 시 `NEWS_SUMMARIZER_DIR/data`를 읽어 `articles` 테이블에 `SUM-001` 같은 id로 주입합니다.
   - summarizer 데이터가 없으면 기존 fallback seed를 사용합니다.
4. `apps/test-frontend`
   - `/v1/users/{user_id}/feed`, detail, scrap, archive API를 통해 backend가 만든 실제 뉴스 데이터를 보여줍니다.

주의: `apps/frontend`는 기존 Next.js 앱이므로 이번 API 검증 작업에서는 건드리지 않습니다. 백엔드 연동 검증은 `apps/test-frontend`만 사용합니다.

## 개발

```bash
# 백엔드 서버 (http://127.0.0.1:8000)
make dev-backend

# 크롤러 서버 (http://localhost:8001)
make dev-crawler

# 기존 Next.js 프론트엔드 (http://localhost:3000)
make dev-frontend

# 백엔드 API 연동 검증용 Vite 프론트엔드 (http://127.0.0.1:5173)
make dev-test-frontend
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

# API 검증용 프론트엔드만 테스트/빌드
make test-test-frontend
make build-test-frontend
```

## API 문서

- Backend: http://localhost:8000/docs
- Crawler: http://localhost:8001/docs
