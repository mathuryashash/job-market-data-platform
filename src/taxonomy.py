"""
Skill taxonomy for job posting classification.
Deterministic regex-based approach — no ML, fully testable.
Organized by category so the mart can filter by skill type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SkillEntry:
    name: str
    category: str
    pattern: re.Pattern = field(repr=False)


# Skills listed from most to least specific (order matters for first-match)
_RAW: list[tuple[str, str, str]] = [
    # Languages
    ("Python", "language", r"\bpython\b"),
    ("Java", "language", r"\bjava\b(?!script)"),
    ("JavaScript", "language", r"\bjavascript\b|\bjs\b"),
    ("TypeScript", "language", r"\btypescript\b|\bts\b"),
    # "go" is an ordinary English word ("go to market", "go-live"), so match only the
    # capitalised language name (case-sensitive via (?-i:...)) or "golang".
    ("Go", "language", r"\bgolang\b|(?-i:\bGo\b)(?![- ]?(?:to|live|getter|ahead|beyond)\b)"),
    ("Rust", "language", r"\brust\b"),
    ("Scala", "language", r"\bscala\b"),
    ("C++", "language", r"\bc\+\+\b|\bcpp\b"),
    ("C#", "language", r"\bc#\b|\bdotnet\b|\.net\b"),
    ("Ruby", "language", r"\bruby\b"),
    ("R", "language", r"\bR\b(?= programming| language)"),
    ("SQL", "language", r"\bsql\b"),
    ("Bash", "language", r"\bbash\b|\bshell\b|\bshell scripting\b"),
    # Data / Big Data
    ("Apache Spark", "data", r"\bapache spark\b|\bpyspark\b|\bspark\b"),
    ("Apache Kafka", "data", r"\bapache kafka\b|\bkafka\b"),
    ("Apache Airflow", "data", r"\bairflow\b|\bapache airflow\b"),
    ("dbt", "data", r"\bdbt\b"),
    ("Apache Flink", "data", r"\bflink\b|\bapache flink\b"),
    ("Hadoop", "data", r"\bhadoop\b|\bhdfs\b|\bhive\b|\bpig\b"),
    ("DBT", "data", r"\bdbt\b"),
    ("Snowflake", "data", r"\bsnowflake\b"),
    ("BigQuery", "data", r"\bbigquery\b"),
    ("Redshift", "data", r"\bredshift\b"),
    ("duckdb", "data", r"\bduckdb\b"),
    ("Databricks", "data", r"\bdatabricks\b"),
    ("Delta Lake", "data", r"\bdelta lake\b|\bdelta table\b"),
    ("Apache Iceberg", "data", r"\biceberg\b"),
    ("Pandas", "data", r"\bpandas\b"),
    ("NumPy", "data", r"\bnumpy\b"),
    # ML / AI
    ("PyTorch", "ml", r"\bpytorch\b"),
    ("TensorFlow", "ml", r"\btensorflow\b"),
    ("scikit-learn", "ml", r"\bscikit.learn\b|\bsklearn\b"),
    ("Hugging Face", "ml", r"\bhugging face\b|\bhuggingface\b|\btransformers\b"),
    ("LLM", "ml", r"\bllm\b|\blarge language model\b"),
    ("RAG", "ml", r"\brag\b|\bretrieval augmented\b"),
    ("MLflow", "ml", r"\bmlflow\b"),
    ("Kubeflow", "ml", r"\bkubeflow\b"),
    # Cloud
    ("AWS", "cloud", r"\baws\b|\bamazon web services\b"),
    ("GCP", "cloud", r"\bgcp\b|\bgoogle cloud\b"),
    ("Azure", "cloud", r"\bazure\b|\bmicrosoft azure\b"),
    ("Kubernetes", "cloud", r"\bkubernetes\b|\bk8s\b"),
    ("Docker", "cloud", r"\bdocker\b"),
    ("Terraform", "cloud", r"\bterraform\b"),
    ("Helm", "cloud", r"\bhelm\b"),
    # Databases
    ("PostgreSQL", "database", r"\bpostgres(ql)?\b|\bpg\b"),
    ("MySQL", "database", r"\bmysql\b"),
    ("MongoDB", "database", r"\bmongodb\b"),
    ("Redis", "database", r"\bredis\b"),
    ("Elasticsearch", "database", r"\belasticsearch\b|\bopensearch\b"),
    ("Cassandra", "database", r"\bcassandra\b"),
    ("ClickHouse", "database", r"\bclickhouse\b"),
    # Backend frameworks
    ("FastAPI", "backend", r"\bfastapi\b"),
    ("Django", "backend", r"\bdjango\b"),
    ("Flask", "backend", r"\bflask\b"),
    ("Spring Boot", "backend", r"\bspring boot\b|\bspring\b"),
    ("Node.js", "backend", r"\bnode\.?js\b"),
    ("gRPC", "backend", r"\bgrpc\b"),
    ("REST API", "backend", r"\brest(ful)? api\b|\brest api\b"),
    ("GraphQL", "backend", r"\bgraphql\b"),
    # DevOps / Observability
    ("CI/CD", "devops", r"\bci\/cd\b|\bcicd\b|\bcontinuous integration\b|\bcontinuous delivery\b"),
    ("GitHub Actions", "devops", r"\bgithub actions\b"),
    ("Prometheus", "devops", r"\bprometheus\b"),
    ("Grafana", "devops", r"\bgrafana\b"),
    ("OpenTelemetry", "devops", r"\bopentelemetry\b|\botel\b"),
    # Soft skills / processes
    ("System Design", "engineering", r"\bsystem design\b"),
    ("Microservices", "engineering", r"\bmicroservices?\b"),
    ("Distributed Systems", "engineering", r"\bdistributed systems?\b"),
    ("Data Engineering", "engineering", r"\bdata engineer(ing)?\b"),
    ("Data Science", "engineering", r"\bdata science\b|\bdata scientist\b"),
    ("Machine Learning", "engineering", r"\bmachine learning\b|\bml\b"),
    ("ETL", "engineering", r"\betl\b|\belt\b|\bextract.transform.load\b"),
    ("Data Modeling", "engineering", r"\bdata model(ing)?\b"),
    ("Data Pipelines", "engineering", r"\bdata pipelines?\b|\bpipelines?\b"),
    ("Stream Processing", "engineering", r"\bstream processing\b|\bstreaming\b"),
]

TAXONOMY: list[SkillEntry] = [
    SkillEntry(name=name, category=cat, pattern=re.compile(pat, re.IGNORECASE))
    for name, cat, pat in _RAW
]


def extract_skills(text: str) -> list[str]:
    """Extract skill names from a job description text.

    Uses the TAXONOMY regex list; returns deduplicated skill names
    preserving order of first match.
    """
    if not text:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for entry in TAXONOMY:
        if entry.name not in seen and entry.pattern.search(text):
            seen.add(entry.name)
            result.append(entry.name)
    return result
