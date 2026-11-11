.PHONY: all install lint test test-unit dbt-build dbt-test up down report bench clean help

PYTHON := python
DBT_DIR := dbt
DUCKDB_PATH ?= $(DBT_DIR)/job_market.duckdb

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## Install Python dependencies
	pip install -r requirements.txt

lint: ## Run ruff linter
	ruff check src/ tests/ scripts/ dashboard/ airflow/dags/
	ruff format --check src/ tests/ scripts/ dashboard/ airflow/dags/

lint-fix: ## Auto-fix lint issues
	ruff check --fix src/ tests/ scripts/ dashboard/ airflow/dags/
	ruff format src/ tests/ scripts/ dashboard/ airflow/dags/

test-unit: ## Run unit tests (no network, no Docker)
	pytest tests/test_taxonomy.py tests/test_normalizers.py tests/test_extractors.py -v

test-spark: ## Run Spark transform tests (needs Java)
	pytest tests/test_spark_transform.py -v

test-dag: ## Run Airflow DAG integrity tests
	pytest tests/test_dag_integrity.py -v

test: ## Run all non-integration tests
	pytest tests/ -v --ignore=tests/test_integration_kafka.py --ignore=tests/test_e2e.py

test-integration: ## Run Kafka integration tests (needs Docker Compose up)
	INTEGRATION=1 KAFKA_BOOTSTRAP=localhost:19092 MINIO_ENDPOINT=http://localhost:19000 \
	pytest tests/test_integration_kafka.py -v

dbt-seed: ## Load fixture seed data into DuckDB
	cd $(DBT_DIR) && DUCKDB_PATH=$(DUCKDB_PATH) dbt seed --profiles-dir . --target duckdb

dbt-build: dbt-seed ## Build dbt models on the seed fixture (no MinIO needed)
	cd $(DBT_DIR) && DUCKDB_PATH=$(DUCKDB_PATH) dbt build --profiles-dir . --target duckdb --vars '{use_fixture: true}' --exclude "source:*"

dbt-build-silver: ## Build dbt models on real silver Parquet (needs `make up` + a pipeline run)
	cd $(DBT_DIR) && DUCKDB_PATH=$(DUCKDB_PATH) dbt build --profiles-dir . --target duckdb

dbt-test: ## Run dbt tests
	cd $(DBT_DIR) && DUCKDB_PATH=$(DUCKDB_PATH) dbt test --profiles-dir . --target duckdb

up: ## Start Docker Compose services (Kafka + MinIO)
	docker compose up -d jmdp-kafka jmdp-minio jmdp-minio-init

down: ## Stop Docker Compose services
	docker compose down

dashboard: ## Start Streamlit dashboard
	DUCKDB_PATH=$(DUCKDB_PATH) streamlit run dashboard/app.py --server.port 18300 --server.headless true

report: ## Print data quality report
	DUCKDB_PATH=$(DUCKDB_PATH) $(PYTHON) -m scripts.report

e2e: ## Run live end-to-end pipeline (needs network)
	$(PYTHON) -m scripts.run_e2e

bench: test bench-normalizers ## Run all benchmarks

bench-normalizers: ## Benchmark normalizers (throughput)
	$(PYTHON) -c "
import time
from src.normalizers import detect_seniority, normalize_location
titles = ['Senior Engineer', 'Intern', 'New Grad SDE', 'Backend Developer'] * 2500
locs = ['Bengaluru, India', 'Remote', 'San Francisco', 'Berlin'] * 2500
t = time.time()
for t_ in titles: detect_seniority(t_)
for l_ in locs: normalize_location(l_)
elapsed = time.time() - t
print(f'Normalizers: 10000 ops in {elapsed:.3f}s = {10000/elapsed:.0f} ops/sec')
"

clean: ## Remove build artifacts
	rm -rf dbt/target dbt/dbt_packages dbt/logs .scratch __pycache__ .pytest_cache
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

secrets-check: ## Check for secrets before committing
	gitleaks detect --source . --no-banner
	git grep -nE "D:/|C:/Users|gsk_|AIza|nvapi-|sk-" -- . ':!*.md' || true
