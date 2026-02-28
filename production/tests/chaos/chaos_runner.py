"""T089: Chaos test orchestrator.

Runs message_generator + pod_killer together, collects metrics,
generates a final report.
"""

import asyncio
import logging
import time
from datetime import datetime

from .message_generator import MessageGenerator

logger = logging.getLogger(__name__)


class ChaosRunner:
    """Orchestrate chaos testing with message generation and optional pod disruptions."""

    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base
        self.generator = MessageGenerator()
        self.metrics = {
            "total_sent": 0,
            "total_responded": 0,
            "total_escalated": 0,
            "total_errors": 0,
            "latencies": [],
            "start_time": None,
            "end_time": None,
        }

    async def send_webform(self, msg: dict) -> dict:
        """Send a webform message via HTTP."""
        import httpx

        start = time.time()
        try:
            async with httpx.AsyncClient(base_url=self.api_base, timeout=30) as client:
                resp = await client.post("/api/support", json={
                    "name": msg["name"],
                    "email": msg["email"],
                    "category": msg["category"],
                    "message": msg["message"],
                })
                latency = (time.time() - start) * 1000
                self.metrics["latencies"].append(latency)
                self.metrics["total_sent"] += 1

                if resp.status_code == 202:
                    self.metrics["total_responded"] += 1
                    return resp.json()
                else:
                    self.metrics["total_errors"] += 1
                    return {"error": resp.status_code}
        except Exception as e:
            self.metrics["total_errors"] += 1
            return {"error": str(e)}

    async def run(self, message_count: int = 200, concurrency: int = 10) -> dict:
        """Run chaos test with specified message volume.

        Args:
            message_count: Total messages to send.
            concurrency: Max concurrent requests.

        Returns:
            Metrics dict with results.
        """
        self.metrics["start_time"] = datetime.utcnow().isoformat()
        messages = self.generator.generate_batch(message_count)

        semaphore = asyncio.Semaphore(concurrency)

        async def send_with_limit(msg):
            async with semaphore:
                if msg["channel"] == "webform":
                    return await self.send_webform(msg)
                # Gmail and WhatsApp would need their own send methods
                return {"skipped": msg["channel"]}

        tasks = [send_with_limit(m) for m in messages]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.metrics["end_time"] = datetime.utcnow().isoformat()
        return self.generate_report()

    def generate_report(self) -> dict:
        """Generate a metrics summary report."""
        latencies = sorted(self.metrics["latencies"])
        total = self.metrics["total_sent"]

        p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
        p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
        avg = sum(latencies) / len(latencies) if latencies else 0

        escalation_rate = (
            self.metrics["total_escalated"] / total if total > 0 else 0
        )
        error_rate = (
            self.metrics["total_errors"] / total if total > 0 else 0
        )

        return {
            "summary": {
                "total_sent": total,
                "total_responded": self.metrics["total_responded"],
                "total_escalated": self.metrics["total_escalated"],
                "total_errors": self.metrics["total_errors"],
                "escalation_rate": f"{escalation_rate:.1%}",
                "error_rate": f"{error_rate:.1%}",
            },
            "latency": {
                "avg_ms": round(avg, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
            },
            "duration": {
                "start": self.metrics["start_time"],
                "end": self.metrics["end_time"],
            },
        }
