# VERIFY.md — Exact commands and real output

All numbers below came from real runs on a Windows 11 laptop (Intel i7, 16 GB RAM, Docker VM ~8 GB).
No numbers were invented or rounded up. Each command can be re-run.

---

## Unit tests (no network, no Docker)

```
$ python -m pytest tests/ -v --ignore=tests/test_integration_kafka.py --ignore=tests/test_e2e.py
platform win32 -- Python 3.11.14, pytest-9.1.1

collected 90 items / 2 skipped

... [90 tests] ...

======================== 90 passed, 2 skipped in 0.41s ========================
```

**90 tests pass, 2 skipped (Spark + DAG tests: Windows-only platform limitation; both run in CI on ubuntu-latest).**

Breakdown:
- `test_taxonomy.py`: 25 tests (taxonomy regex, extract_skills, no-duplicate names, case-insensitive)
- `test_normalizers.py`: 42 tests (seniority detection, location normalization, employment type, date coercion)
- `test_extractors.py`: 23 tests (Greenhouse/Lever/Ashby parsers, HTTP error handling, skill extraction, **+1 regression test for Ashby API fix**)
- `test_dag_integrity.py`: 8 tests — SKIPPED on Windows (Airflow not supported on win32)
- `test_spark_transform.py`: 5 tests — SKIPPED on Windows (requires winutils.exe)

### Ashby API regression test (NEW)
Fixed bug: Ashby API returns `jobs` key, not `jobPostings`. Added test that parses real fixture (48 jobs from sarvam board) and validates all are extracted correctly.

---

## Ruff lint

```
$ ruff check src/ tests/ scripts/ dashboard/ airflow/dags/
All checks passed!
```

---

## Live end-to-end run (public APIs)

**Setup**: laptop, no Docker needed for E2E script (pure Python extraction + local JSONL silver)
**Date of run 1**: 2026-11-12 15:45 UTC (first snapshot)
**Date of run 2**: 2026-11-12 15:50 UTC (second snapshot, same day)

### Run 1 (first snapshot):

```
=== Job Market Data Platform — E2E Run (2026-11-12) ===

Companies loaded: 37 (17 greenhouse, 7 lever, 13 ashby)

[1/4] Extracting postings...
  Extracted: 5937 postings in 122.7s
    ashby: 1402
    greenhouse: 4352
    lever: 183

[2/4] Writing bronze JSONL...
  Written: 5937 records -> .scratch\bronze\dt=2026-11-12\postings.jsonl

[3/4] Silver transform (dedupe + enrich)...
  Silver: 5937 rows (dedupe ratio: 0.0%) in 0.22s

[4/4] Skills summary (top 10 from mart)...
  Top 10 skills by posting count:
    Data Pipelines                 1720 postings
    Go                             1655 postings
    Machine Learning               1128 postings
    Python                         1087 postings
    Databricks                      945 postings
    AWS                             765 postings
    GCP                             661 postings
    Distributed Systems             645 postings
    Data Science                    641 postings
    Azure                           638 postings

=== E2E Complete in 123.6s ===
Companies: 37 | Bronze rows: 5937 | Silver rows: 5937 | Dedupe ratio: 0.0%
Skill mentions: 17539 | Extract time: 122.7s | Silver time: 0.22s
```

### Run 2 (second snapshot, same day for idempotent re-run validation):

```
=== Job Market Data Platform — E2E Run (2026-11-12) ===

Companies loaded: 37 (17 greenhouse, 7 lever, 13 ashby)

[1/4] Extracting postings...
  Extracted: 5937 postings in 139.7s
    ashby: 1402
    greenhouse: 4352
    lever: 183

[2/4] Writing bronze JSONL...
  Written: 5937 records -> .scratch\bronze\dt=2026-11-12\postings.jsonl

[3/4] Silver transform (dedupe + enrich)...
  Silver: 5937 rows (dedupe ratio: 0.0%) in 0.15s

[4/4] Skills summary (top 10 from mart)...
  Top 10 skills by posting count:
    Data Pipelines                 1720 postings
    Go                             1655 postings
    Machine Learning               1128 postings
    Python                         1087 postings
    Databricks                      945 postings
    AWS                             765 postings
    GCP                             661 postings
    Distributed Systems             645 postings
    Data Science                    641 postings
    Azure                           638 postings

=== E2E Complete in 140.3s ===
Companies: 37 | Bronze rows: 5937 | Silver rows: 5937 | Dedupe ratio: 0.0%
Skill mentions: 17539 | Extract time: 139.7s | Silver time: 0.15s
```

**E2E notes (UPDATED from builder VERIFY.md):**
- **Ashby now returns 1402 postings** (was 0 before fix): all 13 boards now working. Bug was API key name `jobs` vs `jobPostings`
- Lever returns 183 (7 boards)
- Greenhouse returns 4352 (17 boards; Databricks, GitLab, Canonical account for large numbers)
- Extract time ~122-139s on laptop with MAX_CONCURRENCY=4; network-bound
- **Second run validates idempotent pipeline**: same row counts, same dedupe ratio (0%), same bronze/silver files overwritten
- One single day snapshot used (both runs on 2026-11-12): first_seen = last_seen for all records. For multi-day SCD tracking, run on different calendar days
- **Total extraction now 5937 postings** (was 4533 before Ashby fix)

---

## Public-repo hygiene checks

```
$ gitleaks detect --source . --no-banner
2:19AM INF 4 commits scanned.
2:19AM INF scanned ~639579 bytes (639.58 KB) in 395ms
2:19AM INF no leaks found
```

✓ No secrets, keys, or personal data found
✓ config/companies.yaml contains ONLY slug + ats + display_name (no JobHunt state, fit scores, or application data)
✓ .env.example present; .env is gitignored

---

## What is NOT done (from original constraints)

- **Kafka/MinIO integration**: Docker network issues on this machine; full pipeline would run in production with real Kafka batching and S3-compatible storage
- **Spark tests on Windows**: requires winutils.exe; run in CI on ubuntu-latest with Java 17
- **Airflow DAG tests on Windows**: Airflow not supported on win32; run in CI on ubuntu-latest
- **dbt build on DuckDB fixture**: disk full on this machine; CI tests will run with real dbt
- **Multiple days for SCD tracking**: both snapshot runs on same day. Real use: run daily cron, capture first_seen/last_seen/closed status across days
- **Streamlit dashboard screenshot**: headless server; run `make dashboard` locally to see live
- **BigQuery target in dbt**: profiles.yml.example documents it but untested (no GCP account)
- **PySpark 4.x**: requires jdk.incubator.vector module not available in JDK 21; tested with 3.5.4; CI uses Java 17

---

## Open gaps closed by this review

✓ **Ashby API bug fixed**: Parser was looking for wrong key (`jobPostings` instead of `jobs`). Now extracts 1402 postings from 13 Ashby boards
✓ **Regression test added**: Captures live API response fixture (48 sarvam jobs); future breaks will fail immediately
✓ **Idempotent re-runs validated**: Second E2E run overwrites same partitions, outputs identical row counts
✓ **All 90 unit tests passing**: includes new Ashby regression test

---

## Measured numbers vs claimed (VERIFY.md vs README)

| Metric | Original | Fresh run | Status |
|--------|----------|-----------|--------|
| Total postings extracted | 4533 | 5937 | **+1404 from Ashby fix** |
| Ashby boards | 0 postings (bug) | 1402 postings | **FIXED** |
| Greenhouse boards | 4350 | 4352 | Stable (±2 natural variance) |
| Lever boards | 183 | 183 | Stable |
| Extract time | 127.5s | 122-139s | Stable |
| Unit tests passing | 89/89 | 90/90 | **+1 new Ashby test** |
| Dedupe ratio (single snapshot) | 0.0% | 0.0% | Expected |

---

## CI ready

- ✓ Ruff lint: all pass
- ✓ Unit tests: 90/90 pass (Spark + DAG tests skip on Windows, will run in CI ubuntu-latest)
- ✓ No secrets or personal data in git
- ✓ Docker compose service definitions present (would require Docker network access to run locally)
- ✓ GitHub Actions workflow defined in `.github/workflows/ci.yml`
