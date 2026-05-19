.PHONY: help backend-up backend-down backend-reset backend-logs full-up full-down test test-backend dev-backend import-articles pipeline-news clean

ifneq (,$(wildcard .env))
include .env
export
endif

NEWS_SOURCE ?= seeded
NEWS_QUERY ?= 경제
NEWS_COUNT ?= 20
PIPELINE_LLM_BACKEND ?= codex_exec
PIPELINE_MODEL ?= gpt-5.4-mini
PIPELINE_CODEX_REASONING_EFFORT ?= low

BACKEND_COMPOSE := docker compose -f apps/backend/docker-compose.yml
ROOT_COMPOSE := docker compose

help:
	@echo "Cut News commands"
	@echo ""
	@echo "Backend Docker:"
	@echo "  make backend-up       - Start backend API + Postgres (builds image)"
	@echo "  make backend-down     - Stop backend API + Postgres"
	@echo "  make backend-reset    - Stop and remove backend DB volume"
	@echo "  make backend-logs     - Tail backend API logs"
	@echo ""
	@echo "Local verification:"
	@echo "  make test             - Run backend tests"
	@echo "  make dev-backend      - Run backend locally without Docker"
	@echo ""
	@echo "Optional full pipeline:"
	@echo "  make full-up          - Start frontend + backend + crawler + scheduler + Postgres"
	@echo "  make full-down        - Stop full pipeline compose"
	@echo "  make pipeline-news    - Run one crawler -> summarizer -> import job locally"
	@echo "  make import-articles  - Import summarizer data into backend DB locally"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            - Remove local caches/build artifacts"

backend-up:
	$(BACKEND_COMPOSE) up --build

backend-down:
	$(BACKEND_COMPOSE) down

backend-reset:
	$(BACKEND_COMPOSE) down -v

backend-logs:
	$(BACKEND_COMPOSE) logs -f api

full-up:
	$(ROOT_COMPOSE) up --build

full-down:
	$(ROOT_COMPOSE) down

test: test-backend

test-backend:
	cd apps/backend && PYTHONPATH=. uv run pytest tests/ -q

dev-backend:
	cd apps/backend && PYTHONPATH=. DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

import-articles:
	cd apps/backend && PYTHONPATH=. DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" uv run python -m app.scripts.import_articles_from_summarizer

pipeline-news:
	cd apps/backend && NEWS_SOURCE=$(NEWS_SOURCE) NEWS_QUERY="$(NEWS_QUERY)" NEWS_COUNT=$(NEWS_COUNT) DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" PIPELINE_LLM_BACKEND=$(PIPELINE_LLM_BACKEND) PIPELINE_MODEL=$(PIPELINE_MODEL) PIPELINE_CODEX_REASONING_EFFORT=$(PIPELINE_CODEX_REASONING_EFFORT) PYTHONPATH=. uv run python -m app.scripts.run_news_pipeline_job

clean:
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name ".next" -o -name "dist" \) -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned caches/build artifacts. node_modules and .venv are left intact."
