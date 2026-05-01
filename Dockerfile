# syntax=docker/dockerfile:1
FROM python:3.13-slim

# uv: fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml ./
RUN uv pip install --requirements pyproject.toml

COPY run.py ./

USER 1000

ENTRYPOINT ["python", "run.py"]
