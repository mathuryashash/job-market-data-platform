"""
End-to-end test: runs a mini pipeline with Docker Compose services
(Kafka + MinIO) and the real Python stack.
Only runs when INTEGRATION=1 is set (not in normal unit test runs or CI).
"""

from __future__ import annotations

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION") != "1",
    reason="Set INTEGRATION=1 to run integration tests (needs Docker Compose)",
)

KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092")
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://localhost:19000")


def _wait_for_kafka(timeout: int = 60) -> bool:
    """Wait until Kafka is accepting connections."""
    import socket
    host, port = KAFKA_BOOTSTRAP.split(":")
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection((host, int(port)), timeout=2):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(2)
    return False


class TestKafkaProduceConsume:
    """Integration test: produce postings to Kafka, then consume them."""

    def test_produce_and_consume(self):
        from src.extractor import Posting
        from src.lander import consume_and_land
        from src.producer import produce

        assert _wait_for_kafka(), f"Kafka not available at {KAFKA_BOOTSTRAP}"

        # Create a small batch of test postings
        postings = [
            Posting(
                source="greenhouse",
                company="TestCo",
                external_id=str(i),
                title=f"Engineer {i}",
                locations=["Remote"],
                is_remote=True,
                region="remote_global",
                department="Eng",
                employment_type="full_time",
                seniority="mid",
                posted_at="2024-01-15",
                updated_at="2024-01-15",
                url=f"https://example.com/{i}",
                description="Python, Kafka test",
                skills=["Python", "Apache Kafka"],
            )
            for i in range(10)
        ]

        # Produce
        produced = produce(postings, bootstrap_servers=KAFKA_BOOTSTRAP)
        assert produced == 10, f"Expected 10 messages, got {produced}"

        # Consume and land (MinIO must also be up)
        result = consume_and_land(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            max_messages=10,
            run_date="2024-01-15",
        )
        total_landed = sum(result.values())
        assert total_landed == 10, f"Expected 10 landed, got {total_landed}"
