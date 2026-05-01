# syntax=docker/dockerfile:1
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

ENV UV_NO_CACHE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

RUN find /app/.venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /app/.venv -type d -name tests -prune -exec rm -rf {} + \
    && find /app/.venv -type d -name test -prune -exec rm -rf {} + \
    && find /app/.venv -name '*.pyc' -delete

FROM python:3.14-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY run.py ./

ENV PATH="/app/.venv/bin:$PATH"

USER 1000

ENTRYPOINT ["python", "run.py"]
