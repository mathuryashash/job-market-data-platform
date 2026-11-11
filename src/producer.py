"""
Kafka producer: serialize Posting objects to JSON and send to `postings.raw`.
Key = source:company:external_id for deterministic partition assignment.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable

logger = logging.getLogger(__name__)

TOPIC = "postings.raw"


def produce(postings: Iterable, bootstrap_servers: str | None = None) -> int:
    """Produce postings to Kafka. Returns count of messages sent."""
    from kafka import KafkaProducer  # type: ignore

    servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    producer = KafkaProducer(
        bootstrap_servers=servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
        acks="all",
        retries=3,
        max_block_ms=10_000,
    )
    count = 0
    for posting in postings:
        d = posting.to_dict() if hasattr(posting, "to_dict") else posting
        producer.send(TOPIC, key=d["key"], value=d)
        count += 1
        if count % 100 == 0:
            logger.info("produced %d messages so far", count)

    producer.flush()
    producer.close()
    logger.info("produced %d total messages to %s", count, TOPIC)
    return count
