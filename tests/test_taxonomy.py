"""Tests for the skill taxonomy extractor."""

import pytest

from src.taxonomy import TAXONOMY, extract_skills


class TestExtractSkills:
    """Table-driven tests for skill extraction."""

    # (description_text, expected_skills_subset, should_not_contain)
    CASES = [
        (
            "Experience with Python and Apache Spark required. SQL knowledge helpful.",
            ["Python", "Apache Spark", "SQL"],
            [],
        ),
        (
            "Must know Kafka, dbt, and Airflow for this data engineering role.",
            ["Apache Kafka", "dbt", "Apache Airflow"],
            [],
        ),
        (
            "PyTorch and TensorFlow for ML. Deploy on Kubernetes (K8s) with Docker.",
            ["PyTorch", "TensorFlow", "Kubernetes", "Docker"],
            [],
        ),
        (
            "FastAPI backend with PostgreSQL and Redis. CI/CD with GitHub Actions.",
            ["FastAPI", "PostgreSQL", "Redis", "CI/CD", "GitHub Actions"],
            [],
        ),
        (
            # JavaScript should not match Java
            "JavaScript and Node.js developer needed.",
            ["JavaScript", "Node.js"],
            ["Java"],
        ),
        (
            # Empty string
            "",
            [],
            [],
        ),
        (
            # None-like: handled
            "   ",
            [],
            [],
        ),
        (
            "Senior Data Engineer with AWS, GCP, Terraform, and Delta Lake experience.",
            ["AWS", "GCP", "Terraform", "Delta Lake"],
            [],
        ),
        (
            "LLM fine-tuning with Hugging Face transformers for RAG pipelines.",
            ["LLM", "Hugging Face", "RAG"],
            [],
        ),
        (
            "Data pipelines using ETL processes and stream processing with Kafka.",
            ["ETL", "Data Pipelines", "Stream Processing", "Apache Kafka"],
            [],
        ),
    ]

    @pytest.mark.parametrize("text,expected,excluded", CASES)
    def test_extract_skills_contains_expected(self, text, expected, excluded):
        result = extract_skills(text)
        for skill in expected:
            assert skill in result, f"Expected {skill!r} in result for text: {text[:60]!r}"

    @pytest.mark.parametrize("text,expected,excluded", CASES)
    def test_extract_skills_excludes_unexpected(self, text, expected, excluded):
        result = extract_skills(text)
        for skill in excluded:
            assert skill not in result, f"Unexpected {skill!r} found in result for text: {text[:60]!r}"

    def test_extract_skills_no_duplicates(self):
        text = "Python Python Python and more Python development"
        result = extract_skills(text)
        assert result.count("Python") == 1

    def test_extract_skills_returns_list(self):
        result = extract_skills("Python and Java")
        assert isinstance(result, list)

    def test_taxonomy_no_duplicate_names(self):
        names = [e.name for e in TAXONOMY]
        assert len(names) == len(set(names)), "Duplicate skill names in TAXONOMY"

    def test_taxonomy_all_patterns_compile(self):
        """All regex patterns should be valid (they are compiled at import time)."""
        import re
        for entry in TAXONOMY:
            # pattern is already compiled; just verify it matches something
            assert isinstance(entry.pattern, re.Pattern)

    def test_case_insensitive(self):
        result = extract_skills("PYTHON APACHE SPARK SQL")
        assert "Python" in result
        assert "Apache Spark" in result
        assert "SQL" in result


# Regression: the first live run counted "Go" in 1655 postings because the pattern was
# case-insensitive and matched the English verb ("go to market", "Let's go").


@pytest.mark.parametrize("text,expected", [
    ("Experience in Go and Kubernetes", True),
    ("Golang microservices", True),
    ("We build services in Go.", True),
    ("We go to market fast", False),
    ("Let's go!", False),
    ("Go to market strategy", False),
    ("go-live support", False),
])
def test_go_language_not_english_verb(text, expected):
    assert ("Go" in extract_skills(text)) is expected
