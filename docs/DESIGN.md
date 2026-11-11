# Design Notes — Job Market Data Platform

## Why this project

Data engineering (Kafka, Spark, dbt, Airflow) shows up in 15-34% of entry-level JDs. This project builds a small but real end-to-end pipeline on public job posting data, so the resume claim is backed by working code.

## Architecture decisions

### 1. Kafka for ingest, not direct write

**Decision**: Extract to Kafka first, then land to MinIO, rather than writing directly to object storage.

**Why**: Decoupling. The extractor doesn't need to know about MinIO's layout. If the schema changes, old messages can be replayed. At this scale (< 2000 postings/day) Kafka is over-engineering, but the point is to learn the pattern — the same design scales to millions of events.

**What I considered**: Writing JSONL directly from the extractor. Simpler, would work fine. But doesn't demonstrate the stream-land pattern.

### 2. MinIO (S3-compatible) not HDFS

**Decision**: MinIO as the object store.

**Why**: HDFS requires a full Hadoop cluster. MinIO is a single container, fully S3-compatible, so the same `s3a://` paths work locally and in AWS. All the Spark S3A connector configuration is identical.

**Tradeoff**: MinIO doesn't have HDFS's block replication. For a portfolio project running on a laptop, this is fine.

### 3. DuckDB + dbt-duckdb for the mart layer

**Decision**: DuckDB reads Parquet from MinIO via httpfs; dbt-duckdb materializes marts into a `.duckdb` file.

**Why**: At thousands of rows/day, there's no need for a full warehouse. DuckDB reads Parquet directly — no data movement. The `profiles.yml.example` shows how to point this at BigQuery if needed, but I don't have a GCP account to test it.

**What I considered**: Postgres + dbt-postgres. Would work, but adds another service and needs a schema migration step. DuckDB is simpler for this scale.

### 4. Deterministic skill taxonomy (regex, not ML)

**Decision**: 70+ regex patterns organized by category.

**Why**: Fully reproducible, testable with table-driven unit tests, zero inference cost. The alternative (NER or a classifier) would be harder to debug and wouldn't be meaningfully better for this vocabulary.

**Known limitation**: `\bgo\b` can match non-Go-language contexts ("go to the office"). The pattern requires context (` go\b(?= programming| language)`) but that misses most real mentions. Accepted tradeoff.

### 5. One daily batch DAG, not streaming

**Decision**: Airflow daily DAG, not a Flink streaming pipeline.

**Why**: ATS APIs are batch by nature (they don't push events). Polling them more than once a day is impolite. The Kafka consumer does process messages as they arrive, but the trigger is a daily cron.

**What "stream" means here**: Kafka is used so the extractor and lander are decoupled. The lander can process in near-real-time if the extractor runs continuously, but in practice they both run daily.

### 6. Seniority detection from title only

**Decision**: Regex on title, not job description.

**Why**: Job descriptions are noisy ("we work with senior engineers" doesn't mean the role is senior). Title is a cleaner signal. The fallback is `unknown` — honest rather than wrong.

## Failure modes

- **ATS API down**: extractor catches exceptions per-board, logs and continues. One dead board doesn't kill the run.
- **Kafka unavailable**: producer raises after 3 retries + exponential backoff. The DAG marks the task failed, Airflow retries 2× before alerting.
- **MinIO unavailable**: lander fails. Data for that day is lost (not retried from Kafka because offsets were already committed — intentional simplification; real systems would use at-least-once + idempotent upsert).
- **Schema change in an ATS API**: Parquet schema evolution handles new nullable columns. Dropped columns show as null in silver. dbt tests catch unexpected nulls.

## How to scale

1. **More companies**: add entries to `config/companies.yaml`. No code changes needed.
2. **More frequent runs**: change DAG schedule. The pipeline is idempotent (overwrites same-day partitions).
3. **Production Kafka**: replace `localhost:9092` with a managed Kafka (Confluent Cloud, MSK). No code changes — only env var.
4. **Production Spark**: remove `.master("local")`, point to a cluster URL. The S3A config is already there.
5. **BigQuery target**: follow `profiles.yml.example` BigQuery section. The dbt SQL is DuckDB-dialect; some functions (`list_len`, `unnest` on arrays) need BigQuery equivalents.
