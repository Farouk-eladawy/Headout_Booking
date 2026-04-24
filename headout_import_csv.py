import csv
from typing import List, Dict, Optional


def parse_currency(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        s2 = s.strip()
        if s2.startswith("$"):
            s2 = s2[1:]
        s2 = s2.replace(",", "")
        return float(s2) if s2 else None
    except Exception:
        return None


def parse_pax_counts(s: Optional[str]) -> (str, Optional[int]):
    if not s:
        return "", None
    parts = []
    total = 0
    try:
        for token in s.split("/"):
            token = token.strip()
            if not token:
                continue
            # e.g., "2 Adult"
            seg = token.split()
            if len(seg) >= 2 and seg[0].isdigit():
                count = int(seg[0])
                cat = seg[1].capitalize()
                parts.append(f"{cat}:{count}")
                total += count
            else:
                parts.append(token)
        return (", ".join(parts), total if total > 0 else None)
    except Exception:
        return (s, None)


def parse_headout_csv(file_path: str) -> List[Dict]:
    results: List[Dict] = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            booking_id = (row.get("Booking ID") or "").strip()
            if not booking_id:
                continue
            pax_details, total_pax = parse_pax_counts(row.get("Pax Counts"))
            results.append({
                "id": booking_id,
                "booking_id": booking_id,
                "booking_date": (row.get("Booking Date") or "").strip() or None,
                "experience_date": (row.get("Experience Date") or "").strip() or None,
                "time_slot": (row.get("Experience Time") or "").strip() or None,
                "experience_name": (row.get("Experience Name") or "").strip() or None,
                "customer_name": (row.get("Primary Guest Name") or "").strip() or None,
                "customer_email": (row.get("Primary Guest Email") or "").strip() or None,
                "customer_phone": (row.get("Primary Guest Number") or "").strip() or None,
                "pax_details": pax_details or None,
                "total_pax": total_pax,
                "net_price": parse_currency(row.get("Net Price")),
                "retail_price": parse_currency(row.get("Retail Price")),
                "status": (row.get("Booking Status") or "").strip() or None,
                "raw_data": row,
            })
    return results

