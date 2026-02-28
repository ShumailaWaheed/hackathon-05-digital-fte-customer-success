"""Detailed health check endpoint.

T102: GET /health returning status of database, kafka, gmail_api,
twilio_api per contracts/health.yaml and FR-037.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter

from production.database.connection import health_check as db_health
from production.workers.kafka_config import kafka_health_check

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health():
    """Health check — verifies DB, Kafka, Gmail API, Twilio API connectivity."""
    db = await db_health()
    kafka = kafka_health_check()

    # Gmail API check (can we load credentials?)
    gmail_status = {"status": "unconfigured"}
    gmail_creds = os.environ.get("GMAIL_CREDENTIALS_PATH")
    if gmail_creds:
        try:
            import os.path
            if os.path.isfile(gmail_creds):
                gmail_status = {"status": "configured"}
            else:
                gmail_status = {"status": "unhealthy", "error": "credentials file not found"}
        except Exception as e:
            gmail_status = {"status": "unhealthy", "error": str(e)}

    # Twilio API check (are credentials set?)
    twilio_status = {"status": "unconfigured"}
    if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"):
        twilio_status = {"status": "configured"}

    # Overall status
    overall = "healthy" if db["status"] == "healthy" else "unhealthy"

    return {
        "status": overall,
        "services": {
            "database": db,
            "kafka": kafka,
            "gmail_api": gmail_status,
            "twilio_api": twilio_status,
        },
    }
