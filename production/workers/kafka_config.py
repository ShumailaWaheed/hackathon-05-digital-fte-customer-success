"""Kafka producer/consumer setup for 4 topics.

Topics: inbound-messages, outbound-responses, escalations, metrics.
Uses confluent-kafka with KRaft mode (no Zookeeper).

Gracefully degrades if confluent-kafka is not installed or Kafka is unreachable.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

TOPICS = [
    "inbound-messages",
    "outbound-responses",
    "escalations",
    "metrics",
]

BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Try importing confluent_kafka; fall back to stub if unavailable
try:
    from confluent_kafka import Consumer, Producer, KafkaError
    from confluent_kafka.admin import AdminClient, NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    logger.warning("confluent-kafka not installed — Kafka features disabled")
    KAFKA_AVAILABLE = False
    Consumer = None
    Producer = None


class _StubProducer:
    """No-op producer when Kafka is unavailable."""
    def produce(self, **kwargs): pass
    def flush(self, **kwargs): pass


def get_producer():
    """Create a Kafka producer instance (or stub if unavailable)."""
    if not KAFKA_AVAILABLE:
        logger.debug("Using stub Kafka producer")
        return _StubProducer()
    return Producer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "client.id": "fte-producer",
        "acks": "all",
    })


def get_consumer(
    group_id: str,
    topics: list[str] | None = None,
    auto_offset_reset: str = "earliest",
):
    """Create a Kafka consumer instance."""
    if not KAFKA_AVAILABLE:
        raise RuntimeError("confluent-kafka not installed")
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": group_id,
        "auto.offset.reset": auto_offset_reset,
        "enable.auto.commit": True,
        "auto.commit.interval.ms": 5000,
    })
    if topics:
        consumer.subscribe(topics)
    return consumer


def ensure_topics_exist() -> None:
    """Create Kafka topics if they don't already exist."""
    if not KAFKA_AVAILABLE:
        logger.info("Kafka not available — skipping topic creation")
        return
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
    existing = set(admin.list_topics(timeout=10).topics.keys())

    new_topics = []
    for topic in TOPICS:
        if topic not in existing:
            new_topics.append(
                NewTopic(topic, num_partitions=3, replication_factor=1)
            )

    if new_topics:
        futures = admin.create_topics(new_topics)
        for topic_name, future in futures.items():
            try:
                future.result()
                logger.info("Created Kafka topic: %s", topic_name)
            except Exception as e:
                logger.warning("Topic %s creation: %s", topic_name, e)


def publish_message(
    producer, topic: str, value: dict[str, Any], key: str | None = None
) -> None:
    """Publish a JSON message to a Kafka topic."""
    producer.produce(
        topic=topic,
        value=json.dumps(value, default=str).encode("utf-8"),
        key=key.encode("utf-8") if key else None,
    )
    producer.flush(timeout=5)


def consume_messages(consumer, timeout: float = 1.0) -> dict | None:
    """Poll for a single message from Kafka. Returns parsed JSON or None."""
    msg = consumer.poll(timeout=timeout)
    if msg is None:
        return None
    if msg.error():
        if KAFKA_AVAILABLE and msg.error().code() == KafkaError._PARTITION_EOF:
            return None
        logger.error("Kafka consumer error: %s", msg.error())
        return None

    try:
        return json.loads(msg.value().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("Failed to decode Kafka message: %s", e)
        return None


def kafka_health_check() -> dict:
    """Check if Kafka broker is reachable."""
    if not KAFKA_AVAILABLE:
        return {"status": "unavailable", "error": "confluent-kafka not installed"}
    try:
        admin = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
        metadata = admin.list_topics(timeout=5)
        return {
            "status": "healthy",
            "broker_count": len(metadata.brokers),
            "topic_count": len(metadata.topics),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
