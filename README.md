# Job Market Data Platform

A batch + stream data pipeline that tracks public job postings from Greenhouse, Lever, and Ashby ATS boards. Built to learn the data engineering stack properly: Kafka, Spark, dbt, Airflow, Streamlit — on real but small-scale data (thousands of postings/day, not petabytes).

This is a portfolio project. It runs on a laptop with Docker, not in production.

## Architecture

```mermaid
graph LR
    A[ATS APIs\nGreenhouse/Lever/Ashby] -->|HTTP poll| B[Extractor\nPython]
    B -->|JSON| C[Kafka\npostings.raw]
    C -->|Consumer| D[Bronze Layer\nMinIO JSONL]
    D -->|PySpark| E[Silver Layer\nMinIO Parquet]
    E -->|DuckDB httpfs| F[dbt Models\nStaging + Marts]
    F --> G[Streamlit\nDashboard :18300]
    H[Airflow DAG] -->|Orchestrates| B & C & D & E & F
```

## Quickstart

```bash
# 1. Clone and set up
cp .env.example .env
pip install -r requirements.txt

# 2. Start Kafka + MinIO
make up

# 3. Run the full pipeline (live APIs)
make e2e

# 4. Build dbt models on seed data
make dbt-build

# 5. View dashboard
make dashboard
# Open http://localhost:18300

# 6. Data quality report
make report
```

**Real output from one run on this laptop (see VERIFY.md for full output):**

```
Companies loaded: 38 (17 greenhouse, 7 lever, 14 ashby)
Extracted: 1247 postings in 23.4s
Bronze rows: 1247 | Silver rows: 1198 | Dedupe ratio: 3.9%

Top 10 skills:
  Python                          312 postings
  SQL                             198 postings
  ...
```

## Results

| Stage         | Rows   | Notes                              |
|---------------|--------|------------------------------------|
| Bronze (raw)  | ~1200  | One snapshot, laptop, no Kafka     |
| Silver        | ~1180  | After dedupe (3-5% ratio typical)  |
| dbt mart      | varies | Fixture seed: 10 rows; live: ~1180 |

*Numbers from VERIFY.md. Single snapshot — first_seen = last_seen for all records. Run twice on different days to see SCD-style tracking.*

## Design Decisions

See [docs/DESIGN.md](docs/DESIGN.md) for full reasoning. Short version:

- **Kafka instead of direct write**: keeps extract and land decoupled; lets replay on schema changes
- **MinIO not HDFS**: S3-compatible object store, simpler ops, same API as AWS S3
- **DuckDB not Postgres for dbt**: reads Parquet directly via httpfs; no warehouse needed for this scale
- **Deterministic skill taxonomy**: regex over ML — reproducible, testable, no inference cost
- **One daily DAG**: batch is fine at this scale; stream processing (Flink) would be over-engineering

## Limitations / What's Next

- Single snapshot only: time-to-close and SCD tracking requires multiple daily runs
- No auth-required ATS boards (Naukri, LinkedIn) — only public APIs
- Spark runs in local mode (no cluster); for production add YARN or Databricks
- Airflow runs in standalone/LocalExecutor mode — not production-grade HA
- Skill taxonomy is regex-based: false positives exist (e.g. `\bgo\b` matches non-Go contexts)
- Dashboard has no auth; fine for local/portfolio use

## MIT License

Copyright (c) 2024 Yashash Mathur. See [LICENSE](LICENSE).
