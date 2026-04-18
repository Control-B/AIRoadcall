FROM python:3.12-slim

WORKDIR /app

# Keep image setup minimal and deterministic across backend and worker deploys.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/app/.venv/bin:$PATH"

COPY . /app/

RUN if [ -f /app/agent_worker.py ]; then \
			python -m pip install --no-cache-dir uv && \
			uv sync --no-dev; \
		elif [ -f /app/backend/requirements.txt ]; then \
			pip install --no-cache-dir -r /app/backend/requirements.txt; \
		else \
			echo "Unsupported Docker build context" && exit 1; \
		fi

EXPOSE 10000

# Render/DO inject PORT for backend; the worker path ignores it.
CMD ["sh", "-c", "if [ -f /app/agent_worker.py ]; then exec python agent_worker.py start; else cd /app/backend && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}; fi"]
