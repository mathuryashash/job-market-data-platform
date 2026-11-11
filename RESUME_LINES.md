# Resume Lines

## Bullets (≤ 30 words each)

- Built a job-market data pipeline (Kafka, MinIO, PySpark, dbt/DuckDB); live extraction pulled 5937 postings from 37 ATS boards (Greenhouse/Lever/Ashby) in 123 s.
- Implemented deterministic skill taxonomy (70+ regex patterns, 90 pytest cases: +1 regression test for Ashby); dbt models with 24/24 data-quality tests on fixture data using DuckDB httpfs.
- (PENDING: the Airflow DAG and the full Kafka -> Spark -> dbt run have not been executed together yet. Add a bullet only after VERIFY.md shows that run.)

## Honest keyword list (only what the code actually uses and tests)

**Data Engineering**: Apache Kafka, Apache Spark (PySpark), dbt (dbt-duckdb), Apache Airflow, MinIO (S3-compatible), DuckDB, Parquet, JSONL

**Languages**: Python 3.11

**Testing**: pytest (90 unit tests, including +1 Ashby regression), dbt tests (accepted_values, unique, not_null, custom not_future_date), Spark local mode tests

**DevOps/Infra**: Docker Compose, GitHub Actions CI, ruff

**Concepts**: batch pipeline, stream-land pattern, bronze/silver/mart layers, SCD tracking, skill taxonomy, data quality, idempotent partitioning

**NOT proven by this code**: production deployment, real Kafka cluster, BigQuery, streaming Flink, multi-day SCD runs
