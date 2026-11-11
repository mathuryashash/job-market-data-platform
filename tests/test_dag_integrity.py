"""
Airflow DAG integrity tests: DagBag loads, no import errors, expected tasks present.
Run as a plain pytest (no Airflow running).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Airflow only supports POSIX systems; skip these tests on Windows.
# The CI workflow runs them on ubuntu-latest.
if sys.platform == "win32":
    pytest.skip(
        "Airflow does not support Windows (apache/airflow#10388). "
        "DAG integrity tests run in CI on ubuntu-latest.",
        allow_module_level=True,
    )

# Point Airflow at the DAGs folder
DAGS_DIR = str(Path(__file__).parent.parent / "airflow" / "dags")


@pytest.fixture(scope="module")
def dagbag():
    """Load the DagBag from the dags directory."""
    # Suppress Airflow's first-run setup noise
    os.environ.setdefault("AIRFLOW__CORE__UNIT_TEST_MODE", "True")
    os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", "False")
    # Airflow refuses relative sqlite paths, and "sqlite:///:memory:" counts as relative.
    db_path = Path(tempfile.gettempdir()) / "jmdp_airflow_test.db"
    os.environ.setdefault("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", f"sqlite:///{db_path.as_posix()}")

    try:
        from airflow.models import DagBag
    except ImportError:
        pytest.skip("apache-airflow not installed")

    bag = DagBag(dag_folder=DAGS_DIR, include_examples=False)
    return bag


class TestDagIntegrity:
    def test_no_import_errors(self, dagbag):
        assert dagbag.import_errors == {}, (
            f"DAG import errors: {dagbag.import_errors}"
        )

    def test_dag_exists(self, dagbag):
        assert "job_market_daily" in dagbag.dags

    def test_no_cycles(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        # networkx cycle check
        try:
            import networkx as nx  # type: ignore
            G = nx.DiGraph()
            for task in dag.tasks:
                for ds in task.downstream_list:
                    G.add_edge(task.task_id, ds.task_id)
            assert not list(nx.simple_cycles(G)), "DAG has cycles"
        except ImportError:
            # manual cycle check: topological sort raises if cyclic
            dag.topological_sort()

    def test_expected_tasks(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        task_ids = {t.task_id for t in dag.tasks}
        expected = {"extract", "land", "spark_transform", "dbt_build", "dbt_test", "publish"}
        assert expected.issubset(task_ids), f"Missing tasks: {expected - task_ids}"

    def test_task_dependencies(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        task_map = {t.task_id: t for t in dag.tasks}

        # extract -> land
        assert "land" in {t.task_id for t in task_map["extract"].downstream_list}
        # land -> spark_transform
        assert "spark_transform" in {t.task_id for t in task_map["land"].downstream_list}
        # spark_transform -> dbt_build
        assert "dbt_build" in {t.task_id for t in task_map["spark_transform"].downstream_list}

    def test_schedule_is_daily(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        # schedule can be "@daily" or "0 0 * * *"
        assert dag.schedule_interval in ("@daily", "0 0 * * *"), (
            f"Unexpected schedule: {dag.schedule_interval}"
        )

    def test_catchup_disabled(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        assert dag.catchup is False

    def test_retries_configured(self, dagbag):
        dag = dagbag.dags["job_market_daily"]
        for task in dag.tasks:
            assert task.retries >= 1, f"Task {task.task_id} has retries={task.retries}"
