FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:${PATH}"

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY apps/crawler/pyproject.toml apps/crawler/pyproject.toml
RUN uv sync --frozen --package crawler --all-extras --no-install-project

COPY apps/crawler apps/crawler

WORKDIR /app/apps/crawler

EXPOSE 8001

CMD ["uvicorn", "crawler.main:app", "--host", "0.0.0.0", "--port", "8001"]
