"""
Spark transform tests using PySpark in local mode.
No cluster needed; runs in CI with Java installed.
Uses in-memory data (not MinIO) so it works without Docker.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Skip all tests if pyspark is not installed
pyspark = pytest.importorskip("pyspark", reason="pyspark not installed")


@pytest.fixture(scope="module")
def spark():
    """Create a local SparkSession for testing."""
    from pyspark.sql import SparkSession

    spark = (
        SparkSession.builder.appName("test-job-market")
        .master("local[2]")
        .config("spark.sql.shuffle.partitions", "2")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("ERROR")
    yield spark
    spark.stop()


SAMPLE_RECORDS = [
    {
        "key": "greenhouse:Databricks:1001",
        "source": "greenhouse",
        "company": "Databricks",
        "external_id": "1001",
        "title": "Data Engineer",
        "department": "Engineering",
        "employment_type": "full_time",
        "seniority": "mid",
        "is_remote": False,
        "region": "us",
        "posted_at": "2024-01-10",
        "updated_at": "2024-01-12",
        "url": "https://example.com/1001",
        "description": "Spark, Python, Kafka",
        "skills": ["Python", "Apache Spark", "Apache Kafka"],
        "_ingestion_date": "2024-01-15",
        "silver_date": "2024-01-15",
    },
    # Duplicate of above (same key, slightly older) — should be deduped out
    {
        "key": "greenhouse:Databricks:1001",
        "source": "greenhouse",
        "company": "Databricks",
        "external_id": "1001",
        "title": "Data Engineer",
        "department": "Engineering",
        "employment_type": "full_time",
        "seniority": "mid",
        "is_remote": False,
        "region": "us",
        "posted_at": "2024-01-10",
        "updated_at": "2024-01-10",  # older
        "url": "https://example.com/1001",
        "description": "Spark, Python",
        "skills": ["Python", "Apache Spark"],
        "_ingestion_date": "2024-01-15",
        "silver_date": "2024-01-15",
    },
    {
        "key": "ashby:Sarvam AI:2001",
        "source": "ashby",
        "company": "Sarvam AI",
        "external_id": "2001",
        "title": "ML Engineering Intern",
        "department": "AI",
        "employment_type": "internship",
        "seniority": "intern",
        "is_remote": True,
        "region": "india_remote",
        "posted_at": "2024-01-09",
        "updated_at": "2024-01-09",
        "url": "https://example.com/2001",
        "description": "PyTorch LLM",
        "skills": ["Python", "PyTorch", "LLM"],
        "_ingestion_date": "2024-01-15",
        "silver_date": "2024-01-15",
    },
]


def _write_jsonl(records: list[dict], path: Path) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records))


class TestSparkTransform:
    def test_dedupe_keeps_latest(self, spark, tmp_path):
        from src.spark_transform import transform

        input_file = tmp_path / "input.jsonl"
        _write_jsonl(SAMPLE_RECORDS, input_file)
        output_path = str(tmp_path / "output")

        stats = transform(spark, str(input_file), output_path, run_date="2024-01-15")

        assert stats["input_rows"] == 3
        assert stats["output_rows"] == 2  # 1 duplicate removed
        assert stats["dedupe_ratio"] > 0

    def test_output_has_silver_date(self, spark, tmp_path):
        from src.spark_transform import transform

        input_file = tmp_path / "input.jsonl"
        _write_jsonl(SAMPLE_RECORDS[:1], input_file)
        output_path = str(tmp_path / "output")

        transform(spark, str(input_file), output_path, run_date="2024-01-20")

        df = spark.read.parquet(output_path)
        rows = df.collect()
        assert len(rows) == 1
        assert str(rows[0]["silver_date"]) == "2024-01-20"

    def test_skills_column_preserved(self, spark, tmp_path):
        from src.spark_transform import transform

        input_file = tmp_path / "input.jsonl"
        _write_jsonl(SAMPLE_RECORDS, input_file)
        output_path = str(tmp_path / "output")

        transform(spark, str(input_file), output_path, run_date="2024-01-15")

        df = spark.read.parquet(output_path)
        from pyspark.sql import functions as F
        rows = df.filter(F.col("key") == "greenhouse:Databricks:1001").collect()
        assert len(rows) == 1
        assert rows[0]["skills"] is not None

    def test_handles_empty_input(self, spark, tmp_path):
        from src.spark_transform import transform

        input_file = tmp_path / "empty.jsonl"
        input_file.write_text("")
        output_path = str(tmp_path / "output")

        stats = transform(spark, str(input_file), output_path, run_date="2024-01-15")
        assert stats["input_rows"] == 0
        assert stats["output_rows"] == 0

    def test_dedupe_ratio_range(self, spark, tmp_path):
        from src.spark_transform import transform

        input_file = tmp_path / "input.jsonl"
        _write_jsonl(SAMPLE_RECORDS, input_file)
        output_path = str(tmp_path / "output")

        stats = transform(spark, str(input_file), output_path, run_date="2024-01-15")

        assert 0.0 <= stats["dedupe_ratio"] <= 1.0
