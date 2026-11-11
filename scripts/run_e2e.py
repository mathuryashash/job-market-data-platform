"""
End-to-end pipeline runner (live public APIs).
Run with: python -m scripts.run_e2e
Records counts at each stage and prints a summary suitable for VERIFY.md.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main() -> None:
    from src.extractor import extract_all, load_companies

    t0 = time.time()
    today = date.today().isoformat()

    print(f"=== Job Market Data Platform — E2E Run ({today}) ===\n")

    companies = load_companies("config/companies.yaml")
    print(f"Companies loaded: {len(companies)} ({sum(1 for c in companies if c['ats']=='greenhouse')} greenhouse, "
          f"{sum(1 for c in companies if c['ats']=='lever')} lever, "
          f"{sum(1 for c in companies if c['ats']=='ashby')} ashby)")

    # Extract
    print("\n[1/4] Extracting postings...")
    t_extract = time.time()
    postings = list(extract_all(companies))
    extract_time = time.time() - t_extract

    by_source: dict[str, int] = {}
    for p in postings:
        by_source[p.source] = by_source.get(p.source, 0) + 1

    print(f"  Extracted: {len(postings)} postings in {extract_time:.1f}s")
    for src, cnt in sorted(by_source.items()):
        print(f"    {src}: {cnt}")

    # Write to JSONL (bronze layer simulation without Kafka/MinIO)
    print("\n[2/4] Writing bronze JSONL...")
    bronze_dir = Path(".scratch/bronze") / f"dt={today}"
    bronze_dir.mkdir(parents=True, exist_ok=True)
    bronze_file = bronze_dir / "postings.jsonl"
    with open(bronze_file, "w") as f:
        for p in postings:
            f.write(json.dumps(p.to_dict()) + "\n")
    print(f"  Written: {len(postings)} records -> {bronze_file}")

    # Silver (Spark-like dedupe in pure Python for the script)
    print("\n[3/4] Silver transform (dedupe + enrich)...")
    t_silver = time.time()
    seen: dict[str, dict] = {}
    for p in postings:
        d = p.to_dict()
        existing = seen.get(p.key)
        if existing is None or (d.get("updated_at") or "") >= (existing.get("updated_at") or ""):
            seen[p.key] = d

    silver_records = list(seen.values())
    for r in silver_records:
        r["silver_date"] = today

    dedupe_ratio = 1.0 - (len(silver_records) / len(postings)) if postings else 0
    silver_time = time.time() - t_silver
    print(f"  Silver: {len(silver_records)} rows (dedupe ratio: {dedupe_ratio:.1%}) in {silver_time:.2f}s")

    # Write silver JSONL for dbt
    silver_dir = Path(".scratch/silver") / f"silver_date={today}"
    silver_dir.mkdir(parents=True, exist_ok=True)
    silver_file = silver_dir / "postings.jsonl"
    with open(silver_file, "w") as f:
        for r in silver_records:
            f.write(json.dumps(r) + "\n")

    # Skills summary
    print("\n[4/4] Skills summary (top 10 from mart)...")
    skill_counts: dict[str, int] = {}
    for r in silver_records:
        for s in (r.get("skills") or []):
            skill_counts[s] = skill_counts.get(s, 0) + 1

    top10 = sorted(skill_counts.items(), key=lambda x: -x[1])[:10]
    print("  Top 10 skills by posting count:")
    for skill, cnt in top10:
        print(f"    {skill:<30} {cnt:>4} postings")

    total_time = time.time() - t0
    print(f"\n=== E2E Complete in {total_time:.1f}s ===")
    print(f"Companies: {len(companies)}")
    print(f"Bronze rows: {len(postings)}")
    print(f"Silver rows: {len(silver_records)}")
    print(f"Dedupe ratio: {dedupe_ratio:.1%}")
    print(f"Skill mentions: {sum(skill_counts.values())}")
    print(f"Extract time: {extract_time:.1f}s | Silver time: {silver_time:.2f}s")
    print("\nNote: This run uses one snapshot only. first_seen = last_seen for all records.")
    print("Run twice on different days to see SCD-style tracking.")


if __name__ == "__main__":
    main()
