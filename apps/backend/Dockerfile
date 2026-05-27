FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/backend/pyproject.toml apps/backend/pyproject.toml
COPY apps/crawler/pyproject.toml apps/crawler/pyproject.toml
RUN uv sync --frozen --all-packages --all-extras --no-install-project

COPY apps/backend apps/backend
COPY apps/crawler apps/crawler
COPY apps/summarizer apps/summarizer
COPY docker/news-scheduler.sh docker/news-scheduler.sh

WORKDIR /app/apps/backend

EXPOSE 8030

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8030"]
