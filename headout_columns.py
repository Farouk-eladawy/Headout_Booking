"""Map Headout table headers to column indices without fragile substring matches."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional

DEFAULT_INDICES = {
    "booking_date": 2,
    "experience_date": 3,
    "time_slot": 4,
    "booking_id": 5,
    "experience_name": 6,
    "customer_name": 7,
    "pax_number": 8,
    "net_price": 9,
    "retail_price": 10,
    "status": 11,
    "additional_details": 12,
}

# Most specific patterns first. Do not use bare "id" — it matches "Additional".
HEADER_PATTERNS = [
    ("booking_date", [r"booking\s*date", r"booked\s*on", r"^created$"]),
    ("experience_date", [r"experience\s*date", r"travel\s*date", r"tour\s*date", r"^date$"]),
    ("time_slot", [r"^time$", r"time\s*slot", r"^slot$"]),
    ("booking_id", [r"booking\s*(id|nr|no|number|#)", r"^reference$", r"^id$", r"^ref$"]),
    ("experience_name", [r"experience", r"product\s*name", r"^product$", r"^tour$", r"tour\s*name"]),
    ("customer_name", [r"customer", r"guest\s*name", r"traveler\s*name", r"^guest$", r"^name$"]),
    ("pax_number", [r"\bpax\b", r"participant", r"^people$", r"^guests$", r"no\.?\s*of"]),
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


def match_column_indices(headers: Iterable[str]) -> Dict[str, int]:
    """Return 1-based indices keyed like the scraper cell map."""
    indices = dict(DEFAULT_INDICES)
    assigned = set()
    for i, raw in enumerate(headers):
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
