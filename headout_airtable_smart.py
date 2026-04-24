"""
Headout Airtable Sync Manager (Smart Sync Version)
"""

import requests
import logging
from typing import Dict, Optional, List, Set
import json
from urllib.parse import quote
from datetime import datetime, timedelta


class HeadoutAirtableManager:
    """Manages Airtable synchronization for Headout bookings"""
    
    # Map Headout keys to Airtable column names
    # Key: Headout field name
    # Value: List of affected Airtable columns
    FIELD_MAPPING = {
        'status': ['Booking Status'],
        'pax_details': ['ADT', 'CHD', 'STD', 'Inf', 'Youth', 'Total Travelers'],
        'total_pax': ['Total Travelers'],
        'net_price': ['Net Rate'],
        'retail_price': ['Total price USD '],
        'experience_date': ['Date Trip'],
        'time_slot': ['Date Trip'],
        'customer_name': ['Customer Name'],
        'customer_phone': ['Customer Phone'],
        'customer_email': ['Customer Email'],
        'pickup_location': ['Hotel Name'],
        'language': ['Guide'],
        'experience_name': ['trip Name'],
        'option': ['Option'],
        'booking_id': ['Booking Nr.'],
        'agency': ['Agency'],
        'des': ['des']
    }

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
        
    def _get_mapped_fields(self, booking: Dict) -> Dict:
        """Convert Headout booking object to Airtable fields dictionary"""
        
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
                
                try:
                    dt_obj = datetime.strptime(full_str, "%b %d, %Y %I:%M %p")
                except ValueError:
                    # Fallback
                    dt_obj = datetime.strptime(dt_str, "%b %d, %Y")
                
                # Correction: The user says "difference is 2 hours increase".
                # Scraped: 07:00 AM. Airtable shows: 09:00.
                # To make it display "07:00" in Cairo time, we need to send "05:00 UTC".
                from datetime import timedelta
                dt_obj = dt_obj - timedelta(hours=2)
                
                date_trip_iso = dt_obj.isoformat()
            except Exception as e:
                self.logger.warning(f"Failed to parse date for {booking.get('booking_id')}: {e}")
                date_trip_iso = None

        fields = {
            'des': 'Cairo',
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
            
            'Customer Name': booking.get('customer_name'),
            'Customer Phone': booking.get('customer_phone'),
            'Customer Email': booking.get('customer_email'),
        }
        
        # Remove None values
        fields = {k: v for k, v in fields.items() if v is not None}
        return fields
        
    def upsert_booking(self, booking: Dict, changed_keys: Optional[List[str]] = None) -> Dict:
        """
        Create or update booking in Airtable.
        
        Args:
            booking: The booking dictionary from Headout.
            changed_keys: List of keys in 'booking' that have changed since last sync.
                          If None, assumes ALL fields need to be synced (or new record).
                          If empty list [], implies NO fields changed, so we only ensure existence.
        """
        if not self.api_key or not self.base_id:
            return {'success': False, 'error': 'missing_airtable_config'}
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Generate all mapped fields
        all_fields = self._get_mapped_fields(booking)
        
        # Debug: Log fields containing contact info
        if 'Customer Email' in all_fields or 'Customer Phone' in all_fields:
            self.logger.info(f"Preparing info for {booking.get('booking_id')}")
        
        try:
            # We use Booking Nr. for finding records
            params = {
                'filterByFormula': f'{{Booking Nr.}}="{booking.get("booking_id")}"'
            }
            
            find = requests.get(self.api_url, headers=headers, params=params, timeout=30)
            
            if find.status_code == 200:
                data = find.json() or {}
                records = data.get('records') or []
                
                if records:
                    # --- UPDATE EXISTING RECORD ---
                    rid = records[0].get('id')
                    
                    fields_to_update = {}
                    
                    if changed_keys is None:
                        # Full update (legacy/force)
                        fields_to_update = all_fields
                    else:
                        # Smart update: Only fields that depend on changed_keys
                        affected_columns = set()
                        for key in changed_keys:
                            cols = self.FIELD_MAPPING.get(key, [])
                            affected_columns.update(cols)
                        
                        # Filter all_fields to only include those in affected_columns
                        for k, v in all_fields.items():
                            if k in affected_columns:
                                fields_to_update[k] = v
                                
                    if not fields_to_update:
                        self.logger.info(f"Skipping Airtable update for {booking.get('booking_id')} - No relevant changes detected (Human edits preserved).")
                        return {'success': True, 'recordid': rid, 'action': 'skipped_no_changes'}

                    patch = requests.patch(
                        f'{self.api_url}/{rid}',
                        headers=headers,
                        json={'fields': fields_to_update, 'typecast': True},
                        timeout=30
                    )
                    
                    if patch.status_code in (200, 201):
                        self.logger.info(f'✓ Updated: {booking.get("booking_id")} (Fields: {list(fields_to_update.keys())})')
                        return {'success': True, 'recordid': rid, 'action': 'updated'}
                    else:
                        self.logger.error(f"Airtable Update Failed ({patch.status_code}): {patch.text}")
                        return {'success': False, 'code': patch.status_code, 'error': patch.text}
            
            # --- CREATE NEW RECORD ---
            # Always send ALL fields for new records
            create = requests.post(
                self.api_url,
                headers=headers,
                json={'fields': all_fields, 'typecast': True},
                timeout=30
            )
            
            if create.status_code in (200, 201):
                rid = create.json().get('id')
                self.logger.info(f'✓ Created: {booking.get("booking_id")}')
                return {'success': True, 'recordid': rid, 'action': 'created'}
            
            self.logger.error(f"Airtable Create Failed ({create.status_code}): {create.text}")
            return {'success': False, 'code': create.status_code, 'error': create.text}
        
        except Exception as e:
            self.logger.error(f'Airtable error: {e}')
            return {'success': False, 'error': str(e)}
