"""
ATS extractors: fetch job postings from public APIs and normalize
to a common `Posting` schema.
No auth required. Concurrency capped at 4. Retries with backoff.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from src.normalizers import (
    coerce_date,
    detect_seniority,
    normalize_employment_type,
    normalize_location,
)
from src.taxonomy import extract_skills

logger = logging.getLogger(__name__)

UA = "Mozilla/5.0 (compatible; job-market-data-platform/1.0; +https://github.com/yashashm)"
MAX_CONCURRENCY = 4
RETRY_DELAYS = [1, 3, 7]


@dataclass
class Posting:
    source: str
    company: str
    external_id: str
    title: str
    locations: list
    is_remote: bool
    region: str
    department: str
    employment_type: str
    seniority: str
    posted_at: str | None
    updated_at: str | None
    url: str
    description: str
    skills: list

    @property
    def key(self) -> str:
        return f"{self.source}:{self.company}:{self.external_id}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["key"] = self.key
        return d


def _http_get(url: str, retries: int = 3) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    last_exc: Exception = RuntimeError("no attempts")
    for attempt, delay in enumerate([0] + RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                raise  # board not found, don't retry
            last_exc = e
            logger.warning("HTTP %s for %s (attempt %d)", e.code, url, attempt + 1)
        except Exception as e:
            last_exc = e
            logger.warning("Error fetching %s: %s (attempt %d)", url, e, attempt + 1)
    raise last_exc


def _fetch_greenhouse(slug: str, company_name: str) -> list[Posting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        data = _http_get(url)
    except Exception as e:
        logger.error("greenhouse %s: %s", slug, e)
        return []
    postings = []
    for job in data.get("jobs", []):
        loc_name = (job.get("location") or {}).get("name", "")
        loc_info = normalize_location(loc_name)
        content = job.get("content", "") or ""
        postings.append(Posting(
            source="greenhouse",
            company=company_name,
            external_id=str(job.get("id", "")),
            title=job.get("title", ""),
            locations=[loc_name] if loc_name else [],
            is_remote=loc_info["is_remote"],
            region=loc_info["region"],
            department=(job.get("departments") or [{}])[0].get("name", "") if job.get("departments") else "",
            employment_type=normalize_employment_type(None, job.get("title", "")),
            seniority=detect_seniority(job.get("title", "")),
            posted_at=coerce_date(job.get("first_published") or job.get("updated_at")),
            updated_at=coerce_date(job.get("updated_at")),
            url=job.get("absolute_url", ""),
            description=content[:2000],
            skills=extract_skills(f"{job.get('title','')} {content}"),
        ))
    return postings


def _fetch_lever(slug: str, company_name: str) -> list[Posting]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        data = _http_get(url)
    except Exception as e:
        logger.error("lever %s: %s", slug, e)
        return []
    postings = []
    for job in (data if isinstance(data, list) else []):
        locs = job.get("workplaceType", "") or ""
        cats = job.get("categories", {}) or {}
        loc_text = cats.get("location", "") or locs
        loc_info = normalize_location(loc_text)
        desc = " ".join(
            (job.get("descriptionBody", "") or "")
            .replace("<p>", " ").replace("</p>", " ")
            .replace("<li>", " ").replace("</li>", " ")[:2000].split()
        )
        postings.append(Posting(
            source="lever",
            company=company_name,
            external_id=job.get("id", ""),
            title=job.get("text", ""),
            locations=[loc_text] if loc_text else [],
            is_remote=loc_info["is_remote"],
            region=loc_info["region"],
            department=cats.get("department", ""),
            employment_type=normalize_employment_type(cats.get("commitment"), job.get("text", "")),
            seniority=detect_seniority(job.get("text", "")),
            posted_at=coerce_date(
                time.strftime("%Y-%m-%d", time.gmtime(job["createdAt"] / 1000)) if job.get("createdAt") else None
            ),
            updated_at=coerce_date(
                time.strftime("%Y-%m-%d", time.gmtime(job["updatedAt"] / 1000)) if job.get("updatedAt") else None
            ),
            url=job.get("hostedUrl", ""),
            description=desc,
            skills=extract_skills(f"{job.get('text','')} {desc}"),
        ))
    return postings


def _fetch_ashby(slug: str, company_name: str) -> list[Posting]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        data = _http_get(url)
    except Exception as e:
        logger.error("ashby %s: %s", slug, e)
        return []
    postings = []
    for job in data.get("jobPostings", []):
        locs = job.get("locationName", "") or ""
        loc_info = normalize_location(locs)
        desc = (job.get("descriptionHtml", "") or "")
        # strip HTML tags simply
        desc_clean = re.sub(r"<[^>]+>", " ", desc)[:2000] if desc else ""
        postings.append(Posting(
            source="ashby",
            company=company_name,
            external_id=job.get("id", ""),
            title=job.get("title", ""),
            locations=[locs] if locs else [],
            is_remote=loc_info["is_remote"],
            region=loc_info["region"],
            department=job.get("departmentName", ""),
            employment_type=normalize_employment_type(job.get("employmentType"), job.get("title", "")),
            seniority=detect_seniority(job.get("title", "")),
            posted_at=coerce_date(job.get("publishedDate")),
            updated_at=coerce_date(job.get("updatedAt")),
            url=job.get("jobUrl", ""),
            description=desc_clean,
            skills=extract_skills(f"{job.get('title','')} {desc_clean}"),
        ))
    return postings


import re  # noqa: E402  (needed inside functions above, putting here)

_FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever": _fetch_lever,
    "ashby": _fetch_ashby,
}


def load_companies(config_path: str | Path = "config/companies.yaml") -> list[dict]:
    with open(config_path) as f:
        return yaml.safe_load(f)["companies"]


def extract_all(companies: list[dict], max_workers: int = MAX_CONCURRENCY) -> Generator[Posting, None, None]:
    """Yield Posting objects fetched from all boards, respecting concurrency limit."""
    tasks = []
    for co in companies:
        ats = co["ats"]
        if ats in _FETCHERS:
            tasks.append((ats, co["slug"], co["name"]))

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_FETCHERS[ats], slug, name): (ats, slug, name)
            for ats, slug, name in tasks
        }
        for future in as_completed(futures):
            ats, slug, name = futures[future]
            try:
                yield from future.result()
            except Exception as e:
                logger.error("failed %s/%s: %s", ats, slug, e)
