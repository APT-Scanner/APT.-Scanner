
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend /app/backend

COPY alembic.ini /app/backend/alembic.ini
COPY migrations /app/backend/migrations

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

WORKDIR /app/backend

EXPOSE 8000

ENV PORT=8000

CMD ["/app/start.sh"]