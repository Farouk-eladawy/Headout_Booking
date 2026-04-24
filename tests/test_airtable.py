import os
from datetime import datetime
import uuid

from headout_config import HeadoutConfig
from headout_airtable import HeadoutAirtableManager


def test_airtable_upsert_conditional():
    cfg = HeadoutConfig()
    run_flag = (os.getenv("RUN_AIRTABLE_TESTS", cfg.get("RUN_AIRTABLE_TESTS", "false")) or "false").lower()
    if run_flag != "true":
        return

    api_key = cfg.get("AIRTABLE_API_KEY")
    base_id = cfg.get("AIRTABLE_BASE_ID")
    table = cfg.get("AIRTABLE_TABLE", "Headout Bookings")

    assert api_key and base_id

    mgr = HeadoutAirtableManager(api_key=api_key, base_id=base_id, table_name=table)

    booking_id = f"TEST-AIR-{uuid.uuid4().hex[:8]}"
    booking = {
        "id": booking_id,
        "booking_id": booking_id,
        "customer_name": "Test User",
        "experience_name": "Test Experience",
        "experience_id": "EXP-TEST",
        "booking_date": datetime.now().isoformat(),
        "status": "Confirmed",
        "total_pax": 1,
    }

    res = mgr.upsert_booking(booking)
    assert res.get("success") is True

