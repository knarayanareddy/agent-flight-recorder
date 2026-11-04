# Agent Flight Recorder API image — B01 reference build (UNBUILT: no image built or run yet).
# Target runtime: Python 3.12. Non-root user 10001:10001, read-only-friendly layers;
# infra/compose.yaml applies cap_drop ALL, no-new-privileges, tmpfs mounts at runtime.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL="" \
    BASELINE_MODE=private \
    BASELINE_LIVE_ENABLED="false"

# System dependencies for asyncpg/psycopg builds are not needed: wheels are manylinux.
RUN groupadd -g 10001 appuser && \
    useradd -u 10001 -g 10001 -s /usr/sbin/nologin appuser

WORKDIR /app

# Dependency layer first for caching.
COPY requirements.txt requirements.lock.txt requirements-baseline.txt ./
RUN pip install --no-cache-dir --no-compile -r requirements.txt -r requirements-baseline.txt

# Application source and migration definitions (migrations are applied externally,
# on PostgreSQL 16, as the migration owner role — never by the runtime role).
COPY src ./src
COPY database ./database

USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
