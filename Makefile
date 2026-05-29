.PHONY: help backend-up backend-down backend-reset backend-logs full-up full-down local-up local-down local-restart local-status local-ps local-logs local-pipeline local-report local-report-check github-crawl-download local-pipeline-from-github ops-pipeline-from-github db-current db-migrate test test-backend dev-backend import-articles pipeline-news clean

ENV_PRESERVE_VARS := NEWS_SOURCE NEWS_QUERY NEWS_COUNT NEWS_PIPELINE_MAX_ARTICLES NEWS_CRAWL_INPUT_PATH NEWS_CRAWL_REPORT_PATH DATABASE_URL NAVER_CLIENT_ID NAVER_CLIENT_SECRET PIPELINE_LLM_BACKEND PIPELINE_MODEL PIPELINE_CODEX_REASONING_EFFORT PIPELINE_SELECTED_PER_CATEGORY PIPELINE_BEST_OF_N PIPELINE_BEST_OF_SCORE_THRESHOLD PIPELINE_HERMES_PROFILE PIPELINE_HERMES_MODEL PIPELINE_HERMES_PROVIDER RUN_ON_STARTUP CORS_ALLOWED_ORIGINS NEXT_PUBLIC_API_URL
$(foreach v,$(ENV_PRESERVE_VARS),$(eval ENV_ORIGIN_$(v) := $(origin $(v)))$(eval ENV_VALUE_$(v) := $($(v))))

ifneq (,$(wildcard .env))
include .env
export
endif

$(foreach v,$(ENV_PRESERVE_VARS),$(if $(filter environment,$(ENV_ORIGIN_$(v))),$(eval $(v) := $(ENV_VALUE_$(v)))))

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
	@echo "  make local-up         - Start Dockerless frontend + backend + crawler + scheduler"
	@echo "  make local-down       - Stop Dockerless local services"
	@echo "  make local-status     - Show Dockerless local service status"
	@echo "  make local-ps         - Alias for local-status"
	@echo "  make local-logs       - Show Dockerless local logs"
	@echo "  make local-pipeline   - Run one Dockerless crawler -> summarizer -> import job"
	@echo "  make github-crawl-download - Download latest successful GitHub crawler artifact"
	@echo "  make local-pipeline-from-github - Download crawl artifact, then summarize/import locally"
	@echo "  make ops-pipeline-from-github - Scheduled artifact -> import -> report-check wrapper"
	@echo "  make local-report     - Summarize latest local pipeline run_report.json"
	@echo "  make local-report-check - Validate latest pipeline report for ops alerting"
	@echo "  make db-current       - Show current Alembic revision for DATABASE_URL"
	@echo "  make db-migrate       - Run Alembic migrations against DATABASE_URL"
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

local-up:
	python3 scripts/local-compose.py up $(SERVICES)

local-down:
	python3 scripts/local-compose.py down $(SERVICES)

local-restart:
	python3 scripts/local-compose.py restart $(SERVICES)

local-status:
	python3 scripts/local-compose.py status $(SERVICES)

local-ps:
	python3 scripts/local-compose.py ps $(SERVICES)

local-logs:
	python3 scripts/local-compose.py logs $(SERVICES)

local-pipeline:
	python3 scripts/local-compose.py pipeline

github-crawl-download:
	python3 scripts/download-github-crawl-artifact.py

local-pipeline-from-github: github-crawl-download
	NEWS_CRAWL_INPUT_PATH="$(CURDIR)/apps/crawler/output/github-actions/latest.json" NEWS_CRAWL_REPORT_PATH="$(CURDIR)/apps/crawler/output/github-actions/crawl_report.json" python3 scripts/local-compose.py pipeline

ops-pipeline-from-github:
	python3 scripts/run-scheduled-artifact-pipeline.py $(OPS_PIPELINE_ARGS)

local-report:
	python3 scripts/local-compose.py report

local-report-check:
	python3 scripts/check-pipeline-report.py $(REPORT_CHECK_ARGS)

db-current:
	cd apps/backend && PYTHONPATH=. uv run alembic current

db-migrate:
	cd apps/backend && PYTHONPATH=. uv run alembic upgrade head

test: test-backend

test-backend:
	cd apps/backend && PYTHONPATH=. uv run pytest tests/ -q

dev-backend:
	cd apps/backend && PYTHONPATH=. DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8030

import-articles:
	cd apps/backend && PYTHONPATH=. DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" uv run python -m app.scripts.import_articles_from_summarizer

pipeline-news:
	cd apps/backend && NEWS_SOURCE=$(NEWS_SOURCE) NEWS_QUERY="$(NEWS_QUERY)" NEWS_COUNT=$(NEWS_COUNT) NEWS_PIPELINE_MAX_ARTICLES="$(NEWS_PIPELINE_MAX_ARTICLES)" NEWS_CRAWL_INPUT_PATH="$(NEWS_CRAWL_INPUT_PATH)" NEWS_CRAWL_REPORT_PATH="$(NEWS_CRAWL_REPORT_PATH)" DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" PIPELINE_LLM_BACKEND=$(PIPELINE_LLM_BACKEND) PIPELINE_MODEL=$(PIPELINE_MODEL) PIPELINE_CODEX_REASONING_EFFORT=$(PIPELINE_CODEX_REASONING_EFFORT) PIPELINE_SELECTED_PER_CATEGORY="$(PIPELINE_SELECTED_PER_CATEGORY)" PIPELINE_BEST_OF_N="$(PIPELINE_BEST_OF_N)" PIPELINE_BEST_OF_SCORE_THRESHOLD="$(PIPELINE_BEST_OF_SCORE_THRESHOLD)" PIPELINE_HERMES_PROFILE="$(PIPELINE_HERMES_PROFILE)" PIPELINE_HERMES_MODEL="$(PIPELINE_HERMES_MODEL)" PIPELINE_HERMES_PROVIDER="$(PIPELINE_HERMES_PROVIDER)" PYTHONPATH=. uv run python -m app.scripts.run_news_pipeline_job

clean:
	find . -type d \( -name "__pycache__" -o -name ".pytest_cache" -o -name ".mypy_cache" -o -name ".ruff_cache" -o -name ".next" -o -name "dist" \) -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned caches/build artifacts. node_modules and .venv are left intact."
