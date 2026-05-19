from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_root_compose_runs_backend_crawler_summarizer_and_real_frontend():
    compose_text = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    makefile_text = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')

    assert 'api:' in compose_text
    assert 'db:' in compose_text
    assert 'crawler:' in compose_text
    assert 'news-scheduler:' in compose_text
    assert 'frontend:' in compose_text
    assert 'apps/backend/Dockerfile' in compose_text
    assert 'apps/crawler/Dockerfile' in compose_text
    assert 'apps/frontend/Dockerfile' in compose_text
    assert '"3000:3000"' in compose_text
    assert 'NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://127.0.0.1:8000}' in compose_text
    assert 'FRONTEND_APP_URL: http://127.0.0.1:3000' in compose_text
    assert 'CORS_ALLOWED_ORIGINS: http://127.0.0.1:3000,http://localhost:3000' in compose_text
    assert 'apps/summarizer/data:/app/apps/summarizer/data' in compose_text
    assert 'AI_NEWS_GENERATION_TIME: "08:30:00"' in compose_text
    assert 'make full-up          - Start frontend + backend + crawler + scheduler + Postgres' in makefile_text
    assert 'test-frontend:' not in compose_text


def test_frontend_dockerfile_builds_standalone_next_app():
    dockerfile_text = (REPO_ROOT / 'apps' / 'frontend' / 'Dockerfile').read_text(encoding='utf-8')

    assert 'COPY apps/frontend/package.json' in dockerfile_text
    assert 'npm install' in dockerfile_text
    assert 'npm run build' in dockerfile_text
    assert 'apps/frontend/.next/standalone' in dockerfile_text
    assert 'HOSTNAME=0.0.0.0' in dockerfile_text
    assert 'PORT=3000' in dockerfile_text


def test_backend_image_contains_crawler_and_scheduler_entrypoint():
    dockerfile_text = (REPO_ROOT / 'apps' / 'backend' / 'Dockerfile').read_text(encoding='utf-8')

    assert 'COPY apps/crawler apps/crawler' in dockerfile_text
    assert 'COPY docker/news-scheduler.sh' in dockerfile_text


def test_news_scheduler_retries_and_fails_fast_on_startup_smoke_failure():
    scheduler_text = (REPO_ROOT / 'docker' / 'news-scheduler.sh').read_text(encoding='utf-8')
    compose_text = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')

    assert 'PIPELINE_MAX_ATTEMPTS' in compose_text
    assert 'PIPELINE_RETRY_DELAY_SECONDS' in compose_text
    assert 'run_pipeline_with_retries' in scheduler_text
    assert 'attempt ${attempt}/${max_attempts}' in scheduler_text
    assert 'RUN_ON_STARTUP' in scheduler_text
    assert 'run_pipeline_with_retries' in scheduler_text
    assert 'exit 1' in scheduler_text


def test_crawler_image_imports_src_layout_package():
    dockerfile_text = (REPO_ROOT / 'apps' / 'crawler' / 'Dockerfile').read_text(encoding='utf-8')

    assert 'PYTHONPATH="/app/apps/crawler/src"' in dockerfile_text
    assert 'uvicorn", "crawler.main:app"' in dockerfile_text


def test_full_pipeline_exposes_naver_credentials_to_crawler_and_scheduler():
    compose_text = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    env_example_text = (REPO_ROOT / '.env.example').read_text(encoding='utf-8')
    makefile_text = (REPO_ROOT / 'Makefile').read_text(encoding='utf-8')

    assert compose_text.count('NAVER_CLIENT_ID: ${NAVER_CLIENT_ID:-}') == 2
    assert compose_text.count('NAVER_CLIENT_SECRET: ${NAVER_CLIENT_SECRET:-}') == 2
    assert 'NAVER_CLIENT_ID=' in env_example_text
    assert 'NAVER_CLIENT_SECRET=' in env_example_text
    assert 'include .env' in makefile_text
    assert 'export' in makefile_text
