from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_root_compose_runs_backend_crawler_summarizer_without_frontend():
    compose_text = (REPO_ROOT / 'docker-compose.yml').read_text(encoding='utf-8')

    assert 'api:' in compose_text
    assert 'db:' in compose_text
    assert 'crawler:' in compose_text
    assert 'news-scheduler:' in compose_text
    assert 'apps/backend/Dockerfile' in compose_text
    assert 'apps/crawler/Dockerfile' in compose_text
    assert 'apps/summarizer/data:/app/apps/summarizer/data' in compose_text
    assert 'AI_NEWS_GENERATION_TIME: "08:30:00"' in compose_text
    assert 'FRONTEND_APP_URL' not in compose_text
    assert 'test-frontend:' not in compose_text
    assert 'frontend:' not in compose_text


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
