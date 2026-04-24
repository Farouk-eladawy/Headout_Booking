import os
from datetime import datetime
from headout_database import HeadoutDatabase


def test_database_save_and_query(tmp_path):
    db_path = tmp_path / "headout_bookings.db"
    db = HeadoutDatabase(db_path=str(db_path))

    booking = {
        "id": "TEST-DB-1",
        "booking_id": "TEST-DB-1",
        "customer_name": "Test User",
        "customer_phone": "+000000000",
        "customer_email": "test@example.com",
        "experience_name": "Test Experience",
        "experience_id": "EXP-TEST",
        "booking_date": datetime.now().isoformat(),
        "experience_date": datetime.now().isoformat(),
        "time_slot": "10:00",
        "net_price": 10.0,
        "retail_price": 12.0,
        "revenue": 2.0,
        "commission_rate": 20.0,
        "pax_details": "Adult:1",
        "total_pax": 1,
        "language": "EN",
        "pickup_location": "Test",
        "status": "Confirmed",
        "raw_data": {},
    }

    res = db.save_booking(booking)
    assert res.get("success") is True

    rows = db.get_unsynced_bookings()
    assert isinstance(rows, list)
    assert len(rows) >= 1

