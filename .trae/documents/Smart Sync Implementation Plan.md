# Implementation Plan: Smart Sync with Human Edit Preservation

I have analyzed your project and found that the current system blindly overwrites Airtable with Headout data every time it runs (`upsert_booking` sends all fields). This causes your manual edits in Airtable to be lost.

To fix this, I will implement a **Smart Sync** mechanism that uses your local database as a reference point to detect *actual changes* from Headout.

## 1. Logic Change: "Change-Detection" Strategy
Instead of sending everything every time, the system will:
1.  **Check Local History:** Before saving the new Headout data, retrieve the *previous* version from your local SQLite database (`headout_bookings.db`).
2.  **Compare:** Compare the new Headout data with the old local data.
3.  **Selective Update:**
    *   **No Headout Change:** If Headout data hasn't changed (e.g., date is still the same), we **skip** updating that field in Airtable. This preserves your manual changes in Airtable.
    *   **Headout Changed:** If Headout has a *new* update (e.g., customer rescheduled), we **force update** Airtable to reflect the new reality.
    *   **New Booking:** If it's a brand new booking, we send everything.

## 2. Code Modifications

### A. Refactor `HeadoutAirtableManager` (`headout_airtable.py`)
*   Extract the field mapping logic into a separate method `_map_to_airtable_fields`.
*   Modify `upsert_booking` to accept a new parameter `updated_keys` (list of changed fields).
*   Add a mapping configuration to know which Headout fields affect which Airtable columns (e.g., `experience_date` -> `Date Trip`).
*   **Result:** The update request will only contain fields that *actually changed* in Headout.

### B. Update Sync Logic in `HeadoutScraper` (`headout_scraper.py`)
*   Modify `sync_booking` to:
    1.  Get `old_booking` = `db.get_booking(id)`.
    2.  Identify changed fields (e.g., did `status` change? did `time_slot` change?).
    3.  Save `new_booking` to DB (keeping internal records 100% in sync with Headout).
    4.  Call `airtable.upsert_booking(new_booking, changed_fields)` to only push necessary updates.

## 3. Benefit
*   **Human Edits Safe:** If you change the Date in Airtable, and Headout sends the *old* date again, the system sees "Headout didn't change" and **ignores** it, keeping your manual date.
*   **Real Updates Working:** If the customer reschedules on Headout, the system sees "Headout Date Changed" and **overwrites** your manual date (correct behavior).

This achieves your goal of "Internal Update" (tracking Headout state locally) and "One-time Update" (syncing only changes).
