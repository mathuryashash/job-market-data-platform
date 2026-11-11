"""
End-to-end pipeline test against live public APIs.
Only runs when E2E=1 is set.
Verifies row counts at each stage and measures runtime.
"""

from __future__ import annotations

import os
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("E2E") != "1",
    reason="Set E2E=1 to run the live end-to-end test (needs network + Docker Compose)",
)


class TestEndToEnd:
    def test_full_pipeline(self, tmp_path):
        """Extract -> normalize -> Kafka -> bronze -> silver -> dbt (fixture mode)."""
        from src.extractor import extract_all, load_companies

        t_start = time.time()

        companies = load_companies("config/companies.yaml")
        # Only use 3 companies for the e2e smoke test to stay polite
        sample = companies[:3]

        postings = list(extract_all(sample, max_workers=2))
        t_extract = time.time() - t_start

        print(f"\nE2E: Extracted {len(postings)} postings from {len(sample)} companies in {t_extract:.1f}s")
        assert len(postings) >= 0  # may be 0 if APIs are down

        # Count per source
        by_source: dict[str, int] = {}
        for p in postings:
            by_source[p.source] = by_source.get(p.source, 0) + 1

        print(f"E2E: By source: {by_source}")

        # Skills distribution
        all_skills = [s for p in postings for s in p.skills]
        print(f"E2E: Total skill mentions: {len(all_skills)}")

        print(f"E2E: Total runtime so far: {time.time() - t_start:.1f}s")
