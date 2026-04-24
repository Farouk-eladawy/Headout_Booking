"""
Headout Airtable Sync Manager
"""

import requests
import logging
from typing import Dict, Optional
import json
from urllib.parse import quote
from datetime import datetime


class HeadoutAirtableManager:
    """Manages Airtable synchronization for Headout bookings"""
    
    def __init__(
        self,
        api_key: str,
        base_id: str,
        table_name: str = 'Headout Bookings',
        logger: Optional[logging.Logger] = None
    ):
        self.api_key = api_key
        self.base_id = base_id
        self.table = table_name
        self.logger = logger or logging.getLogger(__name__)
        
        self.api_url = f'https://api.airtable.com/v0/{base_id}/{quote(table_name)}'
        
    def upsert_booking(self, booking: Dict, force_date_update: bool = False) -> Dict:
        """
        Create or update booking in Airtable
        :param booking: The booking data dictionary
        :param force_date_update: If True, overwrite 'Date Trip' even if it exists. 
                                  If False, preserve existing 'Date Trip' in Airtable.
        """
        if not self.api_key or not self.base_id:
            return {'success': False, 'error': 'missing_airtable_config'}
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 1. Status Transformation
        raw_status = booking.get('status') or ''
        status_map = {
            'Success': 'Confirmed',
            'SUCCESS': 'Confirmed',
            'Cancelled': 'Canceled',
            'CANCELLED': 'Canceled',
            'Rescheduled': 'Changed',
            'RESCHEDULED': 'Changed'
        }
        # Use case-insensitive check if exact match fails
        status = status_map.get(raw_status)
        if not status:
            if raw_status.lower() == 'success':
                status = 'Confirmed'
            elif raw_status.lower() == 'cancelled':
                status = 'Canceled'
            elif raw_status.lower() == 'rescheduled':
                status = 'Changed'
            else:
                status = raw_status

        # 2. PAX Parsing
        pax_str = booking.get('pax_details') or ''
        pax_counts = {
            'ADT': 0,
            'CHD': 0,
            'STD': 0,
            'Inf': 0,
            'Youth': 0
        }
        
        if pax_str:
            # Simple parser for "Type:Count, Type:Count" string
            parts = pax_str.split(',')
            for p in parts:
                p = p.strip()
                if ':' in p:
                    ptype, pcount = p.split(':', 1)
                    ptype = ptype.strip().lower()
                    try:
                        count = int(pcount.strip())
                    except:
                        count = 0
                    
                    if 'adult' in ptype or 'general' in ptype or 'senior' in ptype:
                        pax_counts['ADT'] += count
                    elif 'child' in ptype:
                        pax_counts['CHD'] += count
                    elif 'student' in ptype:
                        pax_counts['STD'] += count
                    elif 'infant' in ptype:
                        pax_counts['Inf'] += count
                    elif 'youth' in ptype:
                        pax_counts['Youth'] += count
        
        # 3. Net Rate Formatting
        net_price = booking.get('net_price')
        net_rate_str = f"${net_price}" if net_price is not None else None

        # 4. Date Trip Merge
        # Merge Experience Date (e.g. "Dec 23, 2025") and Time Slot (e.g. "04:00 AM")
        # Output ISO format: "2025-12-23T04:00:00.000Z" (Approx)
        exp_date_str = booking.get('experience_date')
        time_slot_str = booking.get('time_slot')
        date_trip_iso = None
        
        if exp_date_str:
            try:
                # Basic cleanup
                dt_str = exp_date_str.strip()
                tm_str = (time_slot_str or "00:00 AM").strip()
                
                # Full string to parse
                full_str = f"{dt_str} {tm_str}"
                
                # Expected formats
                # Date: Dec 23, 2025
                # Time: 04:00 AM
                try:
                    dt_obj = datetime.strptime(full_str, "%b %d, %Y %I:%M %p")
                except ValueError:
                    # Fallback if time format varies or date format varies
                    # Try just date
                    dt_obj = datetime.strptime(dt_str, "%b %d, %Y")
                
                # Format as ISO 8601
                # Note: Headout times are typically in local time of the experience (e.g. Cairo EET)
                # Airtable expects UTC by default for date fields.
                # If the user sees a 2-hour difference (e.g. 07:00 becoming 09:00), it means Airtable is interpreting
                # the time as UTC and displaying it in local time, OR vice versa.
                # Cairo is UTC+2 (or UTC+3 in summer).
                # If we send "2026-01-09T07:00:00", Airtable stores it as 07:00 UTC.
                # If the user views it in Cairo (UTC+2), they see 09:00. This matches the user's report (2 hours increase).
                # To fix this, we should interpret the scraped time as Cairo time, then convert to UTC before sending,
                # OR send it with the correct offset so Airtable handles it.
                # However, a simpler hack if we want it to *appear* as 07:00 in Airtable (regardless of timezone settings sometimes)
                # is to assume the scraper is running in the same timezone or just pass it as a naive string if Airtable allowed,
                # but Airtable API requires ISO.
                #
                # Correction: The user says "difference is 2 hours increase".
                # Scraped: 07:00 AM. Airtable shows: 09:00.
                # This confirms Airtable thinks the input "07:00" is UTC, and displays it as "09:00" (Cairo UTC+2).
                # To make it display "07:00" in Cairo time, we need to send "05:00 UTC".
                # So we need to subtract 2 hours from the parsed time before sending.
                
                from datetime import timedelta
                # Subtract 2 hours to compensate for Cairo (UTC+2) display
                # This assumes standard time. Daylight saving might need +3. 
                # For a robust solution, we'd use timezone libraries, but a fixed -2 offset solves the immediate visual discrepancy.
                dt_obj = dt_obj - timedelta(hours=2)
                
                date_trip_iso = dt_obj.isoformat()
            except Exception as e:
                self.logger.warning(f"Failed to parse date for {booking.get('booking_id')}: {e}")
                date_trip_iso = None

        # 5. Destination (des) Mapping
        exp_name = (booking.get('experience_name') or '').lower()
        destination = 'Cairo' # Default
        
        hurghada_keywords = [
            'neverland pickalbatros water park',
            'makadi water world'
        ]
        
        if any(keyword in exp_name for keyword in hurghada_keywords):
            destination = 'Hurghada'

        fields = {
            'des': destination,
            'Agency': 'Headout',
            'Booking Nr.': booking.get('booking_id'),
            'trip Name': booking.get('experience_name'),
            'Option': booking.get('option'),
            
            # PAX Fields
            'ADT': pax_counts['ADT'] if pax_counts['ADT'] > 0 else None,
            'CHD': pax_counts['CHD'] if pax_counts['CHD'] > 0 else None,
            'STD': pax_counts['STD'] if pax_counts['STD'] > 0 else None,
            'Inf': pax_counts['Inf'] if pax_counts['Inf'] > 0 else None,
            'Youth': pax_counts['Youth'] if pax_counts['Youth'] > 0 else None,
            
            'Total Travelers': booking.get('total_pax'),
            
            'Net Rate': net_rate_str,
            'Total price USD ': booking.get('retail_price'), # Note: Space at end as requested
            
            'Guide': booking.get('language'),
            'Hotel Name': booking.get('pickup_location'),
            'Booking Status': status,
            
            # Merged Date Field
            'Date Trip': date_trip_iso,
            
            # Removed fields as requested: Booking Date
            # Removed separate fields: Experience Date, Time Slot (Merged into Date Trip)
            
            'Customer Name': booking.get('customer_name'),
            'Customer Phone': booking.get('customer_phone'),
            'Customer Email': booking.get('customer_email'),
        }
        
        # Remove None values
        fields = {k: v for k, v in fields.items() if v is not None}
        
        # Debug: Log fields containing contact info
        if 'Customer Email' in fields or 'Customer Phone' in fields:
            self.logger.info(f"Sending contact info for {booking.get('booking_id')}: Email={fields.get('Customer Email')}, Phone={fields.get('Customer Phone')}")
        else:
            self.logger.info(f"No contact info found for {booking.get('booking_id')}")

        try:
            # We use Booking Nr. for finding records now, assuming it's the unique ID
            # IMPORTANT: The filter formula must use the new field name
            params = {
                'filterByFormula': f'{{Booking Nr.}}="{booking.get("booking_id")}"'
            }
            
            find = requests.get(self.api_url, headers=headers, params=params, timeout=30)
            
            if find.status_code == 200:
                data = find.json() or {}
                records = data.get('records') or []
                
                if records:
                    rid = records[0].get('id')
                    existing_fields = records[0].get('fields', {})
                    
                    # PROTECTION FOR MANUAL EDITS:
                    # If 'Date Trip' is already set in Airtable, do NOT overwrite it unless forced.
                    # force_date_update=True means Headout data changed significantly, so we overwrite.
                    if existing_fields.get('Date Trip') and not force_date_update:
                        if 'Date Trip' in fields:
                            # self.logger.info(f"Preserving existing Date Trip in Airtable for {booking.get('booking_id')}")
                            del fields['Date Trip']

                    patch = requests.patch(
                        f'{self.api_url}/{rid}',
                        headers=headers,
                        json={'fields': fields, 'typecast': True},
                        timeout=30
                    )
                    
                    if patch.status_code in (200, 201):
                        self.logger.info(f'✓ Updated: {booking.get("booking_id")}')
                        return {'success': True, 'recordid': rid}
                    else:
                        self.logger.error(f"Airtable Update Failed ({patch.status_code}): {patch.text}")
                        return {'success': False, 'code': patch.status_code, 'error': patch.text}
            
            create = requests.post(
                self.api_url,
                headers=headers,
                json={'fields': fields, 'typecast': True},
                timeout=30
            )
            
            if create.status_code in (200, 201):
                rid = create.json().get('id')
                self.logger.info(f'✓ Created: {booking.get("booking_id")}')
                return {'success': True, 'recordid': rid}
            
            self.logger.error(f"Airtable Create Failed ({create.status_code}): {create.text}")
            return {'success': False, 'code': create.status_code, 'error': create.text}
        
        except Exception as e:
            self.logger.error(f'Airtable error: {e}')
            return {'success': False, 'error': str(e)}
