"""
Data quality report: row counts per stage, dedupe ratio, null rates, freshness.
Run with: python -m scripts.report  or  make report
Reads from DuckDB (built by dbt).
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

DUCKDB_PATH = os.environ.get("DUCKDB_PATH", "dbt/job_market.duckdb")


def main() -> None:
    try:
        import duckdb
    except ImportError:
        print("ERROR: duckdb not installed. Run: pip install duckdb")
        sys.exit(1)

    if not Path(DUCKDB_PATH).exists():
        print(f"ERROR: DuckDB not found at {DUCKDB_PATH}. Run: make dbt-build")
        sys.exit(1)

    conn = duckdb.connect(DUCKDB_PATH, read_only=True)

    def q(sql: str):
        return conn.execute(sql).fetchall()

    print("=" * 60)
    print("Job Market Data Platform — Data Quality Report")
    print(f"Generated: {date.today().isoformat()}")
    print("=" * 60)

    # Row counts per mart
    print("\n--- Row Counts per Mart ---")
    for table in ["stg_postings", "dim_company", "fct_postings_daily", "skill_demand_weekly",
                  "entry_level_india_remote", "time_to_close"]:
        try:
            rows = q(f"SELECT count(*) FROM {table}")[0][0]
            print(f"  {table:<30} {rows:>8,} rows")
        except Exception as e:
            print(f"  {table:<30} ERROR: {e}")

    # Source breakdown
    print("\n--- Postings by Source ---")
    for src, cnt in q("SELECT source, count(*) FROM stg_postings GROUP BY source ORDER BY count(*) DESC"):
        print(f"  {src:<20} {cnt:>6,}")

    # Seniority breakdown
    print("\n--- Postings by Seniority ---")
    for seniority, cnt in q("SELECT seniority, count(*) FROM stg_postings GROUP BY seniority ORDER BY count(*) DESC"):
        print(f"  {seniority:<20} {cnt:>6,}")

    # Null rates
    print("\n--- Null Rates (stg_postings) ---")
    for col in ["posted_at", "department", "skills"]:
        try:
            total = q("SELECT count(*) FROM stg_postings")[0][0]
            nulls = q(f"SELECT count(*) FROM stg_postings WHERE {col} IS NULL")[0][0]
            pct = 100.0 * nulls / total if total else 0
            print(f"  {col:<20} {nulls:>6,} nulls ({pct:.1f}%)")
        except Exception as e:
            print(f"  {col:<20} ERROR: {e}")

    # Top 10 skills
    print("\n--- Top 10 Skills ---")
    for skill, cnt, co_cnt in q("""
        SELECT skill, sum(postings_count), sum(companies_count)
        FROM skill_demand_weekly
        GROUP BY skill ORDER BY sum(postings_count) DESC LIMIT 10
    """):
        print(f"  {skill:<30} {cnt:>5,} postings, {co_cnt:>4,} companies")

    # Freshness
    print("\n--- Data Freshness ---")
    latest = q("SELECT max(silver_date) FROM stg_postings")
    if latest:
        print(f"  Latest silver_date: {latest[0][0]}")

    print("\n" + "=" * 60)
    conn.close()


if __name__ == "__main__":
    main()
