# TrueHold Wellness. Independent Docker build context.
# Base image: https://hub.docker.com/_/python
# Dockerfile reference: https://docs.docker.com/reference/dockerfile/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY wellness_agent ./wellness_agent
COPY thw ./thw
COPY scripts ./scripts

RUN pip install --no-cache-dir . \
    && chmod +x scripts/keep_telegram_poll.sh

CMD ["python", "-u", "-m", "wellness_agent", "telegram-poll"]
