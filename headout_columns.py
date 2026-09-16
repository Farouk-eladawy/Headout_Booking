"""Map Headout table headers to column indices without fragile substring matches."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

# Fallback 1-based td indices for Headout Hub (checkbox header has no matching td).
DEFAULT_INDICES = {
    "experience_date": 1,
    "booking_date": 2,
    "time_slot": 3,
    "booking_id": 4,
    "experience_name": 5,
    "status": 6,
    "pax_number": 7,
    "customer_name": 8,
    "additional_details": 9,
    "net_price": 10,
    "retail_price": 11,
}

# Most specific patterns first. Do not use bare "id" — it matches "Additional".
HEADER_PATTERNS = [
    ("booking_date", [r"booking\s*date", r"booked\s*on", r"^created$"]),
    ("experience_date", [r"experience\s*date", r"travel\s*date", r"tour\s*date", r"^date$"]),
    ("time_slot", [r"^time$", r"time\s*slot", r"^slot$"]),
    ("booking_id", [r"booking\s*(id|nr|no|number|#)", r"^reference$", r"^id$", r"^ref$"]),
    ("experience_name", [r"experience", r"product\s*name", r"^product$", r"^tour$", r"tour\s*name"]),
    ("customer_name", [r"customer", r"guest\s*name", r"traveler\s*name", r"^guest$", r"^name$"]),
    ("pax_number", [r"pax\s*no", r"\bpax\b", r"participant", r"^people$", r"^guests$", r"no\.?\s*of"]),
    ("net_price", [r"net\s*price", r"^net$"]),
    ("retail_price", [r"retail", r"selling\s*price"]),
    ("status", [r"^status$", r"booking\s*status"]),
    ("additional_details", [r"additional", r"^details$"]),
]

HEADOUT_STATUS_WORDS = {
    "success",
    "cancelled",
    "canceled",
    "rescheduled",
    "confirmed",
    "changed",
    "pending",
    "failed",
}

STATUS_MAP = {
    "success": "Confirmed",
    "cancelled": "Canceled",
    "canceled": "Canceled",
    "rescheduled": "Changed",
}

PAX_RE = re.compile(
    r"\d+\s*(adult|child|general|student|infant|senior|youth)",
    re.I,
)


def _norm_header(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def match_column_indices(headers: Iterable[str], cell_count: Optional[int] = None) -> Dict[str, int]:
    """Return 1-based td indices keyed like the scraper cell map.

    Headout's thead often has a leading empty checkbox header with no matching td.
    If cell_count is one less than the header count, skip that empty header so
    Experience maps to the Experience cell instead of Status.
    """
    header_list = [str(h or "") for h in headers]
    skip = 0
    if header_list and not header_list[0].strip():
        if cell_count is None or cell_count == len(header_list) - 1:
            skip = 1
        elif cell_count == len(header_list):
            skip = 0

    indices = dict(DEFAULT_INDICES)
    assigned = set()
    for i, raw in enumerate(header_list[skip:]):
        text = _norm_header(raw)
        if not text:
            continue
        idx = i + 1
        for field, patterns in HEADER_PATTERNS:
            if field in assigned:
                continue
            if any(re.search(pat, text) for pat in patterns):
                indices[field] = idx
                assigned.add(field)
                break
    return indices


def is_status_word(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in HEADOUT_STATUS_WORDS


def looks_like_pax(value: Optional[str]) -> bool:
    return bool(PAX_RE.search(value or ""))


def map_booking_status(raw_status: Optional[str]) -> Optional[str]:
    raw = (raw_status or "").strip()
    if not raw:
        return None
    return STATUS_MAP.get(raw.lower())


def is_valid_experience_name(value: Optional[str]) -> bool:
    text = (value or "").strip()
    if not text or len(text) < 4:
        return False
    if is_status_word(text):
        return False
    if looks_like_pax(text):
        return False
    if re.fullmatch(r"\d{6,12}", text):
        return False
    return True


def is_valid_customer_name(value: Optional[str]) -> bool:
    text = (value or "").strip()
    if not text:
        return False
    if is_status_word(text) or looks_like_pax(text):
        return False
    if re.fullmatch(r"\$?\d[\d.,]*", text):
        return False
    return True


def row_looks_column_shifted(booking: Dict[str, Optional[str]]) -> bool:
    """True when scraped fields landed in the wrong columns."""
    name = booking.get("experience_name")
    status = booking.get("status")
    if is_status_word(name):
        return True
    if looks_like_pax(status) and not is_status_word(status):
        return True
    return False
