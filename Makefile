.PHONY: help install install-backend install-crawler install-frontend
.PHONY: dev dev-backend dev-crawler dev-frontend
.PHONY: lint lint-backend lint-crawler lint-frontend
.PHONY: format format-backend format-crawler
.PHONY: type-check type-check-backend type-check-crawler type-check-frontend
.PHONY: test test-backend test-crawler
.PHONY: clean

help:
	@echo "Cut News Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install           - Install all dependencies"
	@echo "  make install-backend   - Install backend dependencies"
	@echo "  make install-crawler   - Install crawler dependencies"
	@echo "  make install-frontend  - Install frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev-backend       - Run backend dev server (port 8000)"
	@echo "  make dev-crawler       - Run crawler dev server (port 8001)"
	@echo "  make dev-frontend      - Run frontend dev server (port 3000)"
	@echo ""
	@echo "Quality:"
	@echo "  make lint              - Lint all code"
	@echo "  make format            - Format Python code"
	@echo "  make type-check        - Type check all code"
	@echo "  make test              - Run all tests"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean             - Clean build artifacts"

# Installation
install: install-backend install-crawler install-frontend
	@echo "All dependencies installed!"

install-backend:
	cd apps/backend && uv sync --all-extras

install-crawler:
	cd apps/crawler && uv sync --all-extras

install-frontend:
	cd apps/frontend && pnpm install

# Development servers
dev-backend:
	cd apps/backend && uv run uvicorn backend.main:app --reload --port 8000

dev-crawler:
	cd apps/crawler && uv run uvicorn crawler.main:app --reload --port 8001

dev-frontend:
	cd apps/frontend && pnpm dev

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
test: test-backend test-crawler

test-backend:
	cd apps/backend && uv run pytest

test-crawler:
	cd apps/crawler && uv run pytest

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
