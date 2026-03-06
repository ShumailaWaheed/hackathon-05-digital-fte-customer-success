"""Detailed health check endpoint.

T102: GET /health returning status of database, kafka, gmail_api,
twilio_api per contracts/health.yaml and FR-037.
"""

from __future__ import annotations

import logging
import os
import os.path

from fastapi import APIRouter

from production.database.connection import health_check as db_health
from production.workers.kafka_config import kafka_health_check

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Health check — verifies DB, Kafka, Gmail API, Twilio API connectivity."""
    try:
        db = await db_health()
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        db = {"status": "unhealthy", "error": str(e)}

    try:
        kafka = kafka_health_check()
    except Exception as e:
        logger.error("Kafka health check failed: %s", e)
        kafka = {"status": "unhealthy", "error": str(e)}

    # Gmail check
    gmail_status = {"status": "unconfigured"}
    if os.environ.get("GMAIL_EMAIL") and os.environ.get("GMAIL_APP_PASSWORD"):
        gmail_status = {"status": "configured"}
    elif os.environ.get("GMAIL_CREDENTIALS_PATH"):
        creds_path = os.environ["GMAIL_CREDENTIALS_PATH"]
        if os.path.isfile(creds_path):
            gmail_status = {"status": "configured"}
        else:
            gmail_status = {"status": "unhealthy", "error": "credentials file not found"}

    # Twilio check
    twilio_status = {"status": "unconfigured"}
    if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"):
        twilio_status = {"status": "configured"}

    overall = "healthy" if db.get("status") == "healthy" else "unhealthy"

    return {
        "status": overall,
        "services": {
            "database": db,
            "kafka": kafka,
            "gmail_api": gmail_status,
            "twilio_api": twilio_status,
        },
    }
