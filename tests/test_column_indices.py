from headout_columns import (
    header_date_fields,
    is_valid_experience_name,
    match_column_indices,
    map_booking_status,
    parse_booking_row_cells,
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


def test_header_date_fields_follow_active_tab():
    assert header_date_fields(["", "Booking date", "Experience date", "Time slot"]) == [
        "booking_date",
        "experience_date",
    ]
    assert header_date_fields(["", "Experience date", "Booking date", "Time slot"]) == [
        "experience_date",
        "booking_date",
    ]


def test_parse_13_cell_booking_date_tab():
    cells = [
        "",
        "Sep 16, 2026",
        "Sep 23, 2026",
        "07:00 AM",
        "34118146",
        "Combo (Save 5%) : Giza Complex Skip-the-Line Tickets",
        "Success",
        "5 General",
        "Ali Eklof",
        "View contact details",
        "$ 75.00",
        "$ 120.00",
        "",
    ]
    parsed = parse_booking_row_cells(cells, date_fields=["booking_date", "experience_date"])
    assert parsed["booking_id"] == "34118146"
    assert parsed["booking_date"] == "Sep 16, 2026"
    assert parsed["experience_date"] == "Sep 23, 2026"
    assert parsed["time_slot"] == "07:00 AM"
    assert parsed["status"] == "Success"
    assert parsed["pax_number"] == "5 General"
    assert parsed["customer_name"] == "Ali Eklof"
    assert "Giza" in parsed["experience_name"]
    assert not row_looks_column_shifted(parsed)


def test_parse_12_cell_rowspan_booking_date():
    cells = [
        "",
        "Oct 15, 2026",
        "08:00 PM",
        "34115953",
        "Luxury Nile Dinner Cruise in Cairo with Live Entertainment",
        "Success",
        "5 Group",
        "James Schlagheck",
        "Pickup Location: Hilton Cairo Grand Nile",
        "$ 324.99",
        "$ 390.00",
        "",
    ]
    parsed = parse_booking_row_cells(
        cells,
        date_fields=["booking_date", "experience_date"],
        last_dates={"booking_date": "Sep 16, 2026"},
    )
    assert parsed["booking_id"] == "34115953"
    assert parsed["experience_date"] == "Oct 15, 2026"
    assert parsed["booking_date"] == "Sep 16, 2026"
    assert parsed["status"] == "Success"
    assert parsed["experience_name"].startswith("Luxury Nile")
    assert not row_looks_column_shifted(parsed)


def test_parse_12_cell_rowspan_experience_date():
    cells = [
        "",
        "Aug 31, 2026",
        "07:00 AM",
        "33802215",
        "Giza Complex Skip-the-Line Tickets + Access inside the Great Pyramid",
        "Success",
        "3 General",
        "Fedouach Dounya",
        "View contact details",
        "$ 45.00",
        "$ 72.00",
        "",
    ]
    parsed = parse_booking_row_cells(
        cells,
        date_fields=["experience_date", "booking_date"],
        last_dates={"experience_date": "Sep 16, 2026"},
    )
    assert parsed["booking_id"] == "33802215"
    assert parsed["experience_date"] == "Sep 16, 2026"
    assert parsed["booking_date"] == "Aug 31, 2026"
    assert parsed["status"] == "Success"
    assert not row_looks_column_shifted(parsed)
