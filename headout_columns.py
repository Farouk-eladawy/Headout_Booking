"""Map Headout table headers to column indices without fragile substring matches."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence

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
DATE_RE = re.compile(r"^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$")
TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)$", re.I)
BOOKING_ID_RE = re.compile(r"^\d{6,10}$")


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


def header_date_fields(headers: Iterable[str]) -> List[str]:
    """Date columns in Hub header order. The first one is the rowspan/group column."""
    fields: List[str] = []
    for raw in headers:
        text = _norm_header(raw)
        if re.search(r"booking\s*date", text):
            fields.append("booking_date")
        elif re.search(r"experience\s*date|travel\s*date|tour\s*date", text):
            fields.append("experience_date")
    if fields == ["booking_date", "experience_date"] or fields == ["experience_date", "booking_date"]:
        return fields
    return ["experience_date", "booking_date"]


def parse_booking_row_cells(
    cells: Sequence[str],
    date_fields: Optional[Sequence[str]] = None,
    last_dates: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Map a Hub row by cell content so rowspan date cells do not shift Experience/Status."""
    texts = [(c or "").strip() for c in cells]
    ordered = list(date_fields or ["experience_date", "booking_date"])
    if len(ordered) < 2:
        ordered = ["experience_date", "booking_date"]
    prev = last_dates or {}

    out = {
        "booking_date": "",
        "experience_date": "",
        "time_slot": "",
        "booking_id": "",
        "experience_name": "",
        "customer_name": "",
        "pax_number": "",
        "net_price": "",
        "retail_price": "",
        "status": "",
        "additional_details": "",
    }

    id_idx = next((i for i, t in enumerate(texts) if BOOKING_ID_RE.fullmatch(t)), None)
    if id_idx is None:
        return out

    def cell(i: int) -> str:
        if 0 <= i < len(texts):
            return texts[i]
        return ""

    out["booking_id"] = cell(id_idx)
    out["experience_name"] = cell(id_idx + 1)
    out["status"] = cell(id_idx + 2)
    out["pax_number"] = cell(id_idx + 3)
    out["customer_name"] = cell(id_idx + 4)
    out["additional_details"] = cell(id_idx + 5)
    out["net_price"] = cell(id_idx + 6)
    out["retail_price"] = cell(id_idx + 7)

    j = id_idx - 1
    if j >= 0 and TIME_RE.match(texts[j]):
        out["time_slot"] = texts[j]
        j -= 1

    dates: List[str] = []
    while j >= 0 and DATE_RE.match(re.sub(r"\s+", " ", texts[j])):
        dates.insert(0, re.sub(r"\s+", " ", texts[j]))
        j -= 1

    grouped, other = ordered[0], ordered[1]
    if len(dates) >= 2:
        out[grouped] = dates[0]
        out[other] = dates[1]
    elif len(dates) == 1:
        out[other] = dates[0]
        out[grouped] = (prev.get(grouped) or "").strip()

    return out


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
