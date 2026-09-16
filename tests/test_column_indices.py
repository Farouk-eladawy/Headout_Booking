from headout_columns import (
    is_valid_experience_name,
    match_column_indices,
    map_booking_status,
    row_looks_column_shifted,
)


def test_additional_details_does_not_steal_booking_id():
    headers = [
        "",
        "Booking Date",
        "Experience Date",
        "Time",
        "Booking ID",
        "Experience",
        "Customer",
        "Pax",
        "Net Price",
        "Retail Price",
        "Status",
        "Additional Details",
    ]
    idx = match_column_indices(headers, cell_count=len(headers))
    assert idx["booking_id"] == 5
    assert idx["experience_name"] == 6
    assert idx["status"] == 11
    assert idx["additional_details"] == 12


def test_booking_status_header_maps_to_status_not_id():
    headers = ["", "Booking Date", "Booking ID", "Experience", "Booking Status"]
    idx = match_column_indices(headers, cell_count=len(headers))
    assert idx["booking_id"] == 3
    assert idx["status"] == 5


def test_headout_hub_empty_checkbox_header_aligns_to_tds():
    headers = [
        "",
        "Experience date",
        "Booking date",
        "Time slot",
        "Booking ID",
        "Experience",
        "Status",
        "Pax no.",
        "Guest name",
        "Additional details",
        "Net price",
        "Retail price",
        "Action",
    ]
    idx = match_column_indices(headers, cell_count=12)
    assert idx["experience_date"] == 1
    assert idx["booking_date"] == 2
    assert idx["time_slot"] == 3
    assert idx["booking_id"] == 4
    assert idx["experience_name"] == 5
    assert idx["status"] == 6
    assert idx["pax_number"] == 7
    assert idx["customer_name"] == 8
    assert idx["additional_details"] == 9
    assert idx["net_price"] == 10
    assert idx["retail_price"] == 11


def test_shifted_success_into_trip_name():
    assert row_looks_column_shifted({"experience_name": "Success", "status": "3 General"})
    assert not is_valid_experience_name("Success")
    assert map_booking_status("3 General") is None
    assert map_booking_status("Success") == "Confirmed"
    assert is_valid_experience_name("Giza Complex Skip-the-Line Tickets")
