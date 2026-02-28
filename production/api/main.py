"""FastAPI application entry point.

T040: Main app with CORS middleware, webhook routes, structured logging,
startup/shutdown events for DB pool and Kafka topics.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from production.api.routes.webhooks import router as webhook_router
from production.api.routes.reports import router as reports_router
from production.api.middleware.logging import RequestLoggingMiddleware
from production.database.connection import init_pool, close_pool, health_check as db_health
from production.workers.kafka_config import ensure_topics_exist, kafka_health_check

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events for DB pool and Kafka."""
    # Startup
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info("Starting Customer Success FTE API...")

    # Init database pool
    await init_pool()
    logger.info("Database pool initialized")

    # Ensure Kafka topics exist
    try:
        ensure_topics_exist()
        logger.info("Kafka topics verified")
    except Exception as e:
        logger.warning("Kafka topic setup skipped: %s", e)

    yield

    # Shutdown
    logger.info("Shutting down Customer Success FTE API...")
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Customer Success Digital FTE",
    version="1.0.0",
    description="24/7 AI Customer Success agent with omnichannel support",
    lifespan=lifespan,
)

# CORS — allow frontend origin
FRONTEND_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Structured request logging
app.add_middleware(RequestLoggingMiddleware)

# Routes
app.include_router(webhook_router, tags=["support"])
app.include_router(reports_router, tags=["reports"])


@app.get("/health")
async def health():
    """Health check endpoint — verifies DB and Kafka connectivity."""
    db = await db_health()
    kafka = kafka_health_check()
    overall = "healthy" if db["status"] == "healthy" else "unhealthy"
    return {
        "status": overall,
        "database": db,
        "kafka": kafka,
    }
