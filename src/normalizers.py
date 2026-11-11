"""
Normalizers for job posting fields.
Pure functions, fully testable without network.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Seniority detection from job title
# ---------------------------------------------------------------------------

_INTERN_RE = re.compile(r"\bintern\b|\binternship\b|\btrainee\b|\bapprentice\b", re.I)
_NEW_GRAD_RE = re.compile(
    r"\bnew\s*grad\b|\bentry.level\b|\bgraduate\b|\bfresh(er)?\b|\bcampus\b|\buniversity\s+hire\b",
    re.I,
)
_JUNIOR_RE = re.compile(r"\bjunior\b|\bjr\.?\b|\bassociate\b|\bi+\b(?=\s+engineer|\s+developer)", re.I)
_MID_RE = re.compile(r"\bmid.level\b|\bii+\b(?=\s+engineer|\s+developer)|\bstaff\s+(?!eng|data)", re.I)
_SENIOR_RE = re.compile(
    r"\bsenior\b|\bsr\.?\b|\blead\b|\bprincipal\b|\bstaff\s+engineer\b|\bstaff\s+data\b|\bstaff\s+ml\b",
    re.I,
)
_MANAGER_RE = re.compile(r"\bmanager\b|\bdirector\b|\bvp\b|\bhead of\b|\bcto\b", re.I)


def detect_seniority(title: str) -> str:
    """Return one of: intern / new_grad / junior / mid / senior / manager / unknown."""
    if not title:
        return "unknown"
    if _INTERN_RE.search(title):
        return "intern"
    if _NEW_GRAD_RE.search(title):
        return "new_grad"
    if _MANAGER_RE.search(title):
        return "manager"
    if _SENIOR_RE.search(title):
        return "senior"
    if _JUNIOR_RE.search(title):
        return "junior"
    if _MID_RE.search(title):
        return "mid"
    return "unknown"


# ---------------------------------------------------------------------------
# Location normalization
# ---------------------------------------------------------------------------

_INDIA_RE = re.compile(
    r"\bindia\b|\bIN\b|\bbengaluru\b|\bblr\b|\bbangalore\b|\bgurgaon\b|\bgurugram\b"
    r"|\bnoida\b|\bnew delhi\b|\bdelhi\b|\bhyderabad\b|\bpune\b|\bmumbai\b"
    r"|\bchennai\b|\bkolkata\b|\bachennai\b|\bbhubaneswar\b",
    re.I,
)
_REMOTE_RE = re.compile(
    r"\bremote\b|\bwork.from.home\b|\bwfh\b|\banywhere\b|\bworldwide\b|\bglobal\b",
    re.I,
)
_US_RE = re.compile(r"\busa?\b|\bunited states\b|\bsan francisco\b|\bnew york\b|\bseattle\b|\baustin\b", re.I)
_EU_RE = re.compile(r"\beurope\b|\buk\b|\blondon\b|\bberlin\b|\bamsterdam\b", re.I)


def normalize_location(location: str) -> dict:
    """Return {normalized: str, is_remote: bool, is_india: bool, region: str}."""
    loc = location or ""
    is_remote = bool(_REMOTE_RE.search(loc))
    is_india = bool(_INDIA_RE.search(loc))

    if is_india and is_remote:
        region = "india_remote"
    elif is_india:
        region = "india"
    elif is_remote:
        region = "remote_global"
    elif _US_RE.search(loc):
        region = "us"
    elif _EU_RE.search(loc):
        region = "eu"
    elif loc.strip():
        region = "other"
    else:
        region = "unknown"

    normalized = loc.strip() or "Unknown"
    return {
        "normalized": normalized,
        "is_remote": is_remote,
        "is_india": is_india,
        "region": region,
    }


# ---------------------------------------------------------------------------
# Employment type
# ---------------------------------------------------------------------------

_FULLTIME_RE = re.compile(r"\bfull.time\b|\bpermanent\b", re.I)
_PARTTIME_RE = re.compile(r"\bpart.time\b", re.I)
_CONTRACT_RE = re.compile(r"\bcontract\b|\bfreelance\b|\bconsultant\b", re.I)
_INTERNSHIP_RE = re.compile(r"\bintern(ship)?\b", re.I)


def normalize_employment_type(raw: str | None, title: str = "") -> str:
    """Return: full_time / part_time / contract / internship / unknown."""
    combined = f"{raw or ''} {title}"
    if _INTERNSHIP_RE.search(combined):
        return "internship"
    if _CONTRACT_RE.search(combined):
        return "contract"
    if _PARTTIME_RE.search(combined):
        return "part_time"
    if _FULLTIME_RE.search(combined):
        return "full_time"
    return "unknown"


# ---------------------------------------------------------------------------
# Date coercion
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def coerce_date(value: str | None) -> str | None:
    """Extract ISO date prefix (YYYY-MM-DD) from a datetime string, or None."""
    if not value:
        return None
    m = _DATE_RE.match(str(value).strip())
    return m.group(0) if m else None
