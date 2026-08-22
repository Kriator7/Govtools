# Agent North. Independent Docker build context.
# Base image: https://hub.docker.com/_/python
# Dockerfile reference: https://docs.docker.com/reference/dockerfile/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir . \
    && chmod +x scripts/keep_hourly.sh

CMD ["python", "-u", "-m", "mr_north", "hourly-loop"]
