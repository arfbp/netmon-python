FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/backend

RUN addgroup --system app && adduser --system --ingroup app app \
    && mkdir -p /app/data /app/logs \
    && chown -R app:app /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/alembic ./alembic

RUN pip install --upgrade pip \
    && pip install .

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]