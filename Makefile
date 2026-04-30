.PHONY: help install install-backend install-crawler install-frontend install-test-frontend
.PHONY: dev dev-backend dev-crawler dev-frontend dev-test-frontend
.PHONY: lint lint-backend lint-crawler lint-frontend
.PHONY: format format-backend format-crawler
.PHONY: type-check type-check-backend type-check-crawler type-check-frontend
.PHONY: test test-backend test-crawler test-summarizer test-test-frontend build-test-frontend
.PHONY: crawler-collect crawler-export-raw pipeline-summarizer import-articles pipeline-news clean

NEWS_SOURCE ?= seeded
NEWS_QUERY ?= 경제
NEWS_COUNT ?= 20
NEWS_INPUT ?= apps/crawler/output/latest.json
NEWS_RAW_DIR ?= apps/summarizer/data/raw
PIPELINE_LLM_BACKEND ?= codex_exec
PIPELINE_MODEL ?= gpt-5.4-mini
PIPELINE_CODEX_REASONING_EFFORT ?= low

help:
	@echo "Cut News Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install           - Install all dependencies"
	@echo "  make install-backend   - Install backend dependencies"
	@echo "  make install-crawler   - Install crawler dependencies"
	@echo "  make install-frontend  - Install frontend dependencies"
	@echo "  make install-test-frontend - Install API test frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend       - Run backend dev server (port 8000)"
	@echo "  make dev-crawler       - Run crawler dev server (port 8001)"
	@echo "  make dev-frontend      - Run frontend dev server (port 3000)"
	@echo "  make dev-test-frontend - Run API test frontend dev server (port 5173)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint              - Lint all code"
	@echo "  make format            - Format Python code"
	@echo "  make type-check        - Type check all code"
	@echo "  make test              - Run all tests"
	@echo "  make build-test-frontend - Build API test frontend"
	@echo ""
	@echo "Pipeline:"
	@echo "  make crawler-collect NEWS_SOURCE=seeded|naver-search NEWS_QUERY=사회 NEWS_COUNT=20 - Collect real news into apps/crawler/output/latest.json"
	@echo "  make pipeline-summarizer - Run summarizer pipeline over data/raw"
	@echo "  make import-articles    - Import summarizer data into backend DB"
	@echo "  make pipeline-news NEWS_QUERY=사회 NEWS_COUNT=20 - Collect crawler data, summarize, import"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             - Clean build artifacts"

# Installation
install: install-backend install-crawler install-frontend install-test-frontend
	@echo "All dependencies installed!"

install-backend:
	cd apps/backend && uv sync --all-extras

install-crawler:
	cd apps/crawler && uv sync --all-extras

install-frontend:
	cd apps/frontend && pnpm install

install-test-frontend:
	npm --prefix apps/test-frontend install

# Development servers
dev-backend:
	cd apps/backend && python3.11 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-crawler:
	cd apps/crawler && uv run uvicorn crawler.main:app --reload --port 8001

dev-frontend:
	cd apps/frontend && pnpm dev

dev-test-frontend:
	npm --prefix apps/test-frontend run dev -- --host 127.0.0.1

# Linting
lint: lint-backend lint-crawler lint-frontend

lint-backend:
	cd apps/backend && uv run ruff check src tests

lint-crawler:
	cd apps/crawler && uv run ruff check src tests

lint-frontend:
	cd apps/frontend && pnpm lint

# Formatting
format: format-backend format-crawler

format-backend:
	cd apps/backend && uv run ruff format src tests && uv run ruff check --fix src tests

format-crawler:
	cd apps/crawler && uv run ruff format src tests && uv run ruff check --fix src tests

# Type checking
type-check: type-check-backend type-check-crawler type-check-frontend

type-check-backend:
	cd apps/backend && uv run mypy src

type-check-crawler:
	cd apps/crawler && uv run mypy src

type-check-frontend:
	cd apps/frontend && pnpm type-check

# Testing
test: test-backend test-crawler test-summarizer test-test-frontend

test-backend:
	cd apps/backend && PYTHONPATH=. DATABASE_URL=sqlite+pysqlite:///dev-ui-test.db python3.11 -m pytest tests -q

test-crawler:
	cd apps/crawler && PYTHONPATH=src python3.11 -m pytest tests -q

test-summarizer:
	cd apps/summarizer && python3.11 -m pytest tests -q

test-test-frontend:
	npm --prefix apps/test-frontend test

build-test-frontend:
	npm --prefix apps/test-frontend run build

crawler-collect:
	cd apps/crawler && PYTHONPATH=src python3.11 -m crawler.collect_naver --source $(NEWS_SOURCE) --query "$(NEWS_QUERY)" --count $(NEWS_COUNT) --output-dir output

crawler-export-raw:
	cd apps/crawler && PYTHONPATH=src python3.11 -m crawler.export_raw \
		--input ../../$(NEWS_INPUT) \
		--output-dir ../../$(NEWS_RAW_DIR) \
		--clear \
		--clear-derived-dir ../../apps/summarizer/data/json \
		--clear-derived-dir ../../apps/summarizer/data/scored \
		--clear-derived-dir ../../apps/summarizer/data/summarized \
		--clear-derived-dir ../../apps/summarizer/data/verified
	rm -f apps/summarizer/data/category_map.json

pipeline-summarizer:
	cd apps/summarizer && PYTHONUNBUFFERED=1 PIPELINE_LLM_BACKEND=$(PIPELINE_LLM_BACKEND) PIPELINE_MODEL=$(PIPELINE_MODEL) PIPELINE_CODEX_REASONING_EFFORT=$(PIPELINE_CODEX_REASONING_EFFORT) python3.11 run_pipeline.py --from 2

import-articles:
	cd apps/backend && PYTHONPATH=. DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" python3.11 -m app.scripts.import_articles_from_summarizer

pipeline-news:
	cd apps/backend && NEWS_SOURCE=$(NEWS_SOURCE) NEWS_QUERY="$(NEWS_QUERY)" NEWS_COUNT=$(NEWS_COUNT) DATABASE_URL="$${DATABASE_URL:-sqlite+pysqlite:///dev-ui-test.db}" PIPELINE_LLM_BACKEND=$(PIPELINE_LLM_BACKEND) PIPELINE_MODEL=$(PIPELINE_MODEL) PIPELINE_CODEX_REASONING_EFFORT=$(PIPELINE_CODEX_REASONING_EFFORT) PYTHONPATH=. python3.11 -m app.scripts.run_news_pipeline_job

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".next" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".venv" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned!"
