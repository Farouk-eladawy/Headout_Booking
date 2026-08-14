from headout_datetime import cairo_local_to_airtable_iso


def test_summer_dst_eight_pm():
    # Headout: Aug 14, 2026 08:00 PM Cairo (EEST, UTC+3)
    # Airtable should store 17:00 UTC so the UI shows 20:00 EEST.
    assert cairo_local_to_airtable_iso("Aug 14, 2026", "08:00 PM") == "2026-08-14T17:00:00.000Z"
    assert cairo_local_to_airtable_iso("Aug 14, 2026 08:00 PM") == "2026-08-14T17:00:00.000Z"


def test_winter_offset():
    # Cairo winter is EET UTC+2.
    assert cairo_local_to_airtable_iso("Jan 9, 2026", "07:00 AM") == "2026-01-09T05:00:00.000Z"


def test_iso_z_treated_as_cairo_wall_clock():
    assert cairo_local_to_airtable_iso("2026-08-14T20:00:00.000Z") == "2026-08-14T17:00:00.000Z"
    assert cairo_local_to_airtable_iso("2026-08-14T20:00:00+02:00") == "2026-08-14T17:00:00.000Z"
