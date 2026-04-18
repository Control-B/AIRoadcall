# ── Stage 1: Build ──────────────────────────────────────
FROM python:3.12-slim AS builder

RUN python -m pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY . .
RUN uv sync --no-dev

# ── Stage 2: Runtime ───────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# The agent worker is a long-running process that connects to LiveKit Cloud
CMD ["python", "agent_worker.py", "start"]
