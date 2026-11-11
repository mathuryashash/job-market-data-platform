"""
Daily job-market data pipeline DAG.
Tasks: extract >> land >> spark_transform >> dbt_build >> dbt_test >> publish
Each task is idempotent: re-running a day overwrites that day's partition.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

from airflow import DAG

# Shared defaults
DEFAULT_ARGS = {
    "owner": "yashashm",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
}

PROJECT_DIR = "/opt/airflow/project"
PYTHON = "python"


def _extract_and_produce(**context) -> dict:
    """Extract from ATS APIs and produce to Kafka."""
    import sys
    sys.path.insert(0, PROJECT_DIR)

    from src.extractor import extract_all, load_companies
    from src.producer import produce

    ds = context["ds"]  # YYYY-MM-DD
    companies = load_companies(f"{PROJECT_DIR}/config/companies.yaml")
    postings = list(extract_all(companies))
    count = produce(postings)
    return {"date": ds, "extracted": len(postings), "produced": count}


def _land(**context) -> dict:
    """Consume Kafka -> MinIO bronze."""
    import sys
    sys.path.insert(0, PROJECT_DIR)

    from src.lander import consume_and_land

    ds = context["ds"]
    result = consume_and_land(run_date=ds, max_messages=10_000)
    return {"date": ds, "landed": result}


def _spark_transform(**context) -> None:
    """Trigger PySpark bronze -> silver."""
    import subprocess
    ds = context["ds"]
    result = subprocess.run(
        [PYTHON, "-m", "src.spark_transform", "--date", ds],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Spark transform failed:\n{result.stderr}")


def _publish(**context) -> None:
    """Generate data quality report and log summary."""
    import sys
    sys.path.insert(0, PROJECT_DIR)
    # Could write a summary to MinIO or a Slack webhook
    ds = context["ds"]
    print(f"Pipeline complete for {ds}")


with DAG(
    dag_id="job_market_daily",
    description="Daily job market data pipeline: Extract -> Kafka -> Bronze -> Silver -> dbt -> Publish",
    start_date=datetime(2024, 1, 1),
    schedule="@daily",
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["job-market", "data-platform"],
    doc_md="""
## Job Market Daily Pipeline

Fetches postings from public ATS APIs (Greenhouse, Lever, Ashby),
lands them in MinIO, transforms with Spark, models with dbt.

**Idempotent**: re-running a date partition overwrites that day's data.
**Scale**: designed for ~thousands of rows/day (not petabyte-scale).
""",
) as dag:

    t_extract = PythonOperator(
        task_id="extract",
        python_callable=_extract_and_produce,
        doc="Fetch all ATS boards and produce to Kafka `postings.raw`",
    )

    t_land = PythonOperator(
        task_id="land",
        python_callable=_land,
        doc="Consume Kafka -> MinIO bronze (date-partitioned JSONL)",
    )

    t_spark = PythonOperator(
        task_id="spark_transform",
        python_callable=_spark_transform,
        doc="Spark: bronze -> silver (dedupe, normalize, enrich)",
    )

    t_dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {PROJECT_DIR}/dbt && "
            "dbt build --profiles-dir . --target duckdb"
        ),
        doc="Run dbt models + tests in one pass",
    )

    t_dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            f"cd {PROJECT_DIR}/dbt && "
            "dbt test --profiles-dir . --target duckdb"
        ),
        doc="Explicit dbt test run for visibility in Airflow UI",
    )

    t_publish = PythonOperator(
        task_id="publish",
        python_callable=_publish,
        doc="Emit data quality report / summary",
    )

    t_extract >> t_land >> t_spark >> t_dbt_build >> t_dbt_test >> t_publish
