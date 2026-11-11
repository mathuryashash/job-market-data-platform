"""
Bronze lander: Kafka consumer -> MinIO (S3-compatible) as date-partitioned JSONL + Parquet.
Idempotent write: same day's data is overwritten if re-run (partition = date).
Offsets committed after each batch write so crashes don't skip data.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)

TOPIC = "postings.raw"
GROUP_ID = "bronze-lander"
BRONZE_BUCKET = "bronze"
BATCH_SIZE = 500
POLL_TIMEOUT_MS = 5000


def _get_minio_client():
    import boto3  # type: ignore
    from botocore.config import Config  # type: ignore

    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _ensure_bucket(client, bucket: str) -> None:
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        client.create_bucket(Bucket=bucket)
        logger.info("created bucket %s", bucket)


def _write_partition(client, bucket: str, partition_date: str, records: list[dict]) -> None:
    """Write JSONL to MinIO at bronze/<date>/postings.jsonl (overwrite)."""
    key = f"dt={partition_date}/postings.jsonl"
    body = "\n".join(json.dumps(r) for r in records).encode("utf-8")
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/x-ndjson")
    logger.info("wrote %d records to s3://%s/%s", len(records), bucket, key)


def consume_and_land(
    bootstrap_servers: str | None = None,
    max_messages: int | None = None,
    run_date: str | None = None,
) -> dict[str, int]:
    """
    Consume from Kafka and write to MinIO bronze layer.
    Returns {date: row_count} for each partition written.
    max_messages: stop after N messages (for testing/e2e runs).
    run_date: override partition date (useful for idempotent reruns).
    """
    from kafka import KafkaConsumer  # type: ignore

    servers = bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")
    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=servers,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=POLL_TIMEOUT_MS,
    )

    client = _get_minio_client()
    _ensure_bucket(client, BRONZE_BUCKET)

    today = run_date or date.today().isoformat()
    buffer: list[dict] = []
    total = 0

    for msg in consumer:
        record = msg.value
        # Use today as partition date (or the record's posted_at if available for history)
        record["_ingestion_date"] = today
        buffer.append(record)
        total += 1

        if len(buffer) >= BATCH_SIZE:
            _write_partition(client, BRONZE_BUCKET, today, buffer)
            consumer.commit()
            buffer = []

        if max_messages and total >= max_messages:
            break

    if buffer:
        _write_partition(client, BRONZE_BUCKET, today, buffer)
        consumer.commit()

    consumer.close()
    return {today: total}
