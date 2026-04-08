FROM python:3.12-slim

WORKDIR /app

# Keep image setup minimal and deterministic for Render Docker deploys.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/

EXPOSE 10000

# Render injects PORT; default to 10000 for local container runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
