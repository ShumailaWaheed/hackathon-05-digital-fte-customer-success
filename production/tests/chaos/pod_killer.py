"""T088: Kubernetes pod disruption script for chaos testing.

Kills random worker/API pods every N hours to test resilience.
"""

import logging
import random
import subprocess
import time

logger = logging.getLogger(__name__)

NAMESPACE = "customer-success-fte"
TARGET_DEPLOYMENTS = ["api", "worker"]


class PodKiller:
    """Kill random pods in the K8s namespace for chaos testing."""

    def __init__(self, namespace: str = NAMESPACE):
        self.namespace = namespace

    def list_pods(self, deployment: str | None = None) -> list[str]:
        """List running pod names in the namespace."""
        cmd = ["kubectl", "get", "pods", "-n", self.namespace, "-o", "name", "--field-selector=status.phase=Running"]
        if deployment:
            cmd.extend(["-l", f"app={deployment}"])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logger.error("kubectl list failed: %s", result.stderr)
                return []
            return [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        except Exception as e:
            logger.error("Failed to list pods: %s", e)
            return []

    def kill_random_pod(self, deployment: str | None = None) -> str | None:
        """Kill a random running pod. Returns the pod name or None."""
        pods = self.list_pods(deployment)
        if not pods:
            logger.warning("No pods available to kill")
            return None

        target = random.choice(pods)
        logger.info("Killing pod: %s", target)

        try:
            result = subprocess.run(
                ["kubectl", "delete", target, "-n", self.namespace, "--grace-period=0", "--force"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                logger.info("Pod killed: %s", target)
                return target
            else:
                logger.error("Failed to kill pod: %s", result.stderr)
                return None
        except Exception as e:
            logger.error("Pod kill failed: %s", e)
            return None

    def schedule_disruptions(self, interval_hours: float = 2, duration_hours: float = 24) -> list[str]:
        """Run pod kills at regular intervals for the specified duration.

        Returns list of killed pod names.
        """
        killed = []
        start = time.time()
        end = start + (duration_hours * 3600)
        interval_seconds = interval_hours * 3600

        logger.info(
            "Starting chaos: kill every %.1fh for %.1fh",
            interval_hours, duration_hours,
        )

        while time.time() < end:
            deployment = random.choice(TARGET_DEPLOYMENTS)
            pod = self.kill_random_pod(deployment)
            if pod:
                killed.append(pod)

            remaining = end - time.time()
            sleep_time = min(interval_seconds, remaining)
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.info("Chaos complete: %d pods killed", len(killed))
        return killed
