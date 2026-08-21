# Cloud Run / local container image.
# Source: https://cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-python-service
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY templates ./templates
COPY mappings ./mappings
COPY prompts ./prompts
COPY data/imports ./data/imports

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
