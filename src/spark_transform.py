"""
Spark transform: bronze -> silver.
Run via: python -m src.spark_transform [--date YYYY-MM-DD] [--input s3a://...] [--output s3a://...]
In CI/tests, PySpark local mode (no cluster needed).
"""

from __future__ import annotations

import argparse
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)


def get_spark(app_name: str = "job-market-transform"):
    """Create or get SparkSession, configured for MinIO S3A."""
    from pyspark.sql import SparkSession  # type: ignore

    endpoint = os.environ.get("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")

    spark = (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.hadoop.fs.s3a.endpoint", endpoint)
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.aws.credentials.provider",
                "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def transform(
    spark,
    bronze_path: str,
    silver_path: str,
    run_date: str | None = None,
) -> dict:
    """
    Read bronze JSONL, dedupe, enrich, write silver Parquet.
    Returns stats: {input_rows, output_rows, dedupe_ratio}.
    """
    from pyspark.sql import functions as F  # type: ignore
    from pyspark.sql.types import ArrayType, StringType  # type: ignore
    from pyspark.sql.window import Window  # type: ignore

    today = run_date or date.today().isoformat()

    # Read bronze
    df = spark.read.json(bronze_path)
    input_rows = df.count()
    logger.info("bronze rows: %d", input_rows)

    if input_rows == 0:
        logger.warning("no bronze data for %s", bronze_path)
        return {"input_rows": 0, "output_rows": 0, "dedupe_ratio": 0.0}

    # Dedupe: keep latest by key (source:company:external_id)
    w = Window.partitionBy("key").orderBy(F.coalesce("updated_at", "posted_at", F.current_date().cast("string")).desc())
    df = df.withColumn("_rank", F.row_number().over(w)).filter(F.col("_rank") == 1).drop("_rank")

    # Add run metadata
    df = df.withColumn("silver_date", F.lit(today))

    # Normalize skills column: ensure it's always an array
    if "skills" in df.columns:
        df = df.withColumn("skills", F.when(F.col("skills").isNull(), F.array()).otherwise(F.col("skills")))
    else:
        df = df.withColumn("skills", F.array().cast(ArrayType(StringType())))

    # Ensure required columns exist with defaults
    for col_name, default in [
        ("is_remote", False),
        ("region", "unknown"),
        ("seniority", "unknown"),
        ("employment_type", "unknown"),
        ("department", ""),
    ]:
        if col_name not in df.columns:
            df = df.withColumn(col_name, F.lit(default))

    output_rows = df.count()
    dedupe_ratio = round(1.0 - (output_rows / input_rows), 4) if input_rows > 0 else 0.0

    logger.info("silver rows: %d (dedupe ratio: %.2f%%)", output_rows, dedupe_ratio * 100)

    # Write partitioned by silver_date
    df.write.mode("overwrite").partitionBy("silver_date").parquet(silver_path)

    return {
        "input_rows": input_rows,
        "output_rows": output_rows,
        "dedupe_ratio": dedupe_ratio,
    }


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Bronze -> Silver Spark transform")
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--bronze", default=os.environ.get("BRONZE_PATH", "s3a://bronze"))
    parser.add_argument("--silver", default=os.environ.get("SILVER_PATH", "s3a://silver"))
    args = parser.parse_args()

    spark = get_spark()
    stats = transform(spark, args.bronze, args.silver, args.date)
    print(f"Transform complete: {stats}")
    spark.stop()


if __name__ == "__main__":
    main()
