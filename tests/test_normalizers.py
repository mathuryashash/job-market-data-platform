"""Tests for field normalizers."""

import pytest

from src.normalizers import (
    coerce_date,
    detect_seniority,
    normalize_employment_type,
    normalize_location,
)


class TestDetectSeniority:
    CASES = [
        ("Software Engineering Intern", "intern"),
        ("Data Engineering Internship", "intern"),
        ("New Grad Software Engineer", "new_grad"),
        ("Graduate Engineer", "new_grad"),
        ("Junior Developer", "junior"),
        ("Jr. Software Engineer", "junior"),
        ("Associate Engineer", "junior"),
        ("Senior Software Engineer", "senior"),
        ("Sr. Backend Engineer", "senior"),
        ("Lead Data Scientist", "senior"),
        ("Staff Engineer", "senior"),
        ("Principal Engineer", "senior"),
        ("Engineering Manager", "manager"),
        ("VP of Engineering", "manager"),
        ("Head of Data", "manager"),
        ("Software Engineer", "unknown"),
        ("Backend Developer", "unknown"),
        ("", "unknown"),
        (None, "unknown"),
    ]

    @pytest.mark.parametrize("title,expected", CASES)
    def test_detect_seniority(self, title, expected):
        result = detect_seniority(title)
        assert result == expected, f"detect_seniority({title!r}) = {result!r}, expected {expected!r}"


class TestNormalizeLocation:
    CASES = [
        (
            "Bengaluru, India",
            False,  # not remote — it's an on-site India location
            True,
            "india",
        ),
        ("Bangalore", False, True, "india"),
        ("Remote - India", True, True, "india_remote"),
        ("Remote", True, False, "remote_global"),
        ("Work from Home", True, False, "remote_global"),
        ("Anywhere", True, False, "remote_global"),
        ("San Francisco, CA", False, False, "us"),
        ("New York, USA", False, False, "us"),
        ("London, UK", False, False, "eu"),
        ("Berlin, Germany", False, False, "eu"),
        ("Singapore", False, False, "other"),
        ("", False, False, "unknown"),
        (None, False, False, "unknown"),
    ]

    @pytest.mark.parametrize("location,is_remote,is_india,region", CASES)
    def test_normalize_location(self, location, is_remote, is_india, region):
        result = normalize_location(location)
        assert result["is_remote"] == is_remote, f"is_remote for {location!r}"
        assert result["is_india"] == is_india, f"is_india for {location!r}"
        assert result["region"] == region, f"region for {location!r}"

    def test_returns_dict_keys(self):
        result = normalize_location("Bangalore")
        assert set(result.keys()) == {"normalized", "is_remote", "is_india", "region"}

    def test_normalized_strips_whitespace(self):
        result = normalize_location("  Bangalore  ")
        assert result["normalized"] == "Bangalore"

    def test_normalized_fallback_for_empty(self):
        result = normalize_location("")
        assert result["normalized"] == "Unknown"


class TestNormalizeEmploymentType:
    CASES = [
        ("Full-Time", "", "full_time"),
        ("Permanent", "", "full_time"),
        ("Part-Time", "", "part_time"),
        ("Contract", "", "contract"),
        ("Freelance", "", "contract"),
        (None, "Software Engineering Intern", "internship"),
        ("Internship", "", "internship"),
        (None, "", "unknown"),
        ("", "", "unknown"),
        (None, "Full Time Backend Developer", "full_time"),
    ]

    @pytest.mark.parametrize("raw,title,expected", CASES)
    def test_normalize_employment_type(self, raw, title, expected):
        result = normalize_employment_type(raw, title)
        assert result == expected, f"normalize_employment_type({raw!r}, {title!r}) = {result!r}"


class TestCoerceDate:
    CASES = [
        ("2024-01-15T10:30:00Z", "2024-01-15"),
        ("2024-01-15", "2024-01-15"),
        ("2024-01-15T00:00:00+05:30", "2024-01-15"),
        ("", None),
        (None, None),
        ("invalid", None),
        ("not-a-date", None),
    ]

    @pytest.mark.parametrize("value,expected", CASES)
    def test_coerce_date(self, value, expected):
        result = coerce_date(value)
        assert result == expected, f"coerce_date({value!r}) = {result!r}"
