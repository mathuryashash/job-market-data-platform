# Resume Lines

## Bullets (≤ 30 words each)

- Built end-to-end job-market data pipeline: Kafka → MinIO → PySpark → dbt/DuckDB; extracted 4533 postings from 37 companies via public ATS APIs in 128s.
- Implemented deterministic skill taxonomy (70+ regex patterns, 89 pytest cases); dbt models with 24/24 data-quality tests on fixture data using DuckDB httpfs.
- Orchestrated daily Airflow DAG (extract → land → Spark → dbt → publish) with idempotent partitions, retries, and DAG-integrity tests via DagBag.

## Honest keyword list (only what the code actually uses and tests)

**Data Engineering**: Apache Kafka, Apache Spark (PySpark), dbt (dbt-duckdb), Apache Airflow, MinIO (S3-compatible), DuckDB, Parquet, JSONL

**Languages**: Python 3.11

**Testing**: pytest (89 unit tests), dbt tests (accepted_values, unique, not_null, custom not_future_date), Spark local mode tests

**DevOps/Infra**: Docker Compose, GitHub Actions CI, ruff

**Concepts**: batch pipeline, stream-land pattern, bronze/silver/mart layers, SCD tracking, skill taxonomy, data quality, idempotent partitioning

**NOT proven by this code**: production deployment, real Kafka cluster, BigQuery, streaming Flink, multi-day SCD runs
