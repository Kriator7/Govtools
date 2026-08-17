"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import (
    analytics,
    communications,
    documents,
    health,
    investors,
    jobs,
    listings,
    opportunities,
    realtors,
    transactions,
    webhooks,
)
from app.config import get_settings
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Realtor Property Acquisition Automation",
        description=(
            "Automation platform for one Nevada realtor. The system never signs, "
            "submits, or executes a real-estate transaction without explicit realtor approval."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(health.router)
    application.include_router(realtors.router, prefix=settings.api_prefix)
    application.include_router(investors.router, prefix=settings.api_prefix)
    application.include_router(listings.router, prefix=settings.api_prefix)
    application.include_router(opportunities.router, prefix=settings.api_prefix)
    application.include_router(transactions.router, prefix=settings.api_prefix)
    application.include_router(documents.router, prefix=settings.api_prefix)
    application.include_router(communications.router, prefix=settings.api_prefix)
    application.include_router(webhooks.router, prefix=settings.api_prefix)
    application.include_router(jobs.router, prefix=settings.api_prefix)
    application.include_router(analytics.router, prefix=settings.api_prefix)
    return application


app = create_app()
