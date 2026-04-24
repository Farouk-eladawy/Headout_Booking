"""
Headout Bookings Database Manager
SQLite database for storing and managing Headout booking data
"""

import sqlite3
import logging
from typing import Dict, Optional
from datetime import datetime
import json


class HeadoutDatabase:
    """Manages SQLite database for Headout bookings"""
    
    SCHEMA = '''
    CREATE TABLE IF NOT EXISTS bookings (
        -- Primary Keys
        id TEXT PRIMARY KEY,
        booking_id TEXT UNIQUE NOT NULL,
        agency TEXT DEFAULT 'Headout',
        
        -- Customer Information
        customer_name TEXT,
        customer_phone TEXT,
        customer_email TEXT,
        
        -- Booking Details
        experience_name TEXT,
        experience_id TEXT,
        booking_date TEXT,
        experience_date TEXT,
        time_slot TEXT,
        
        -- Financial Data
        net_price REAL,
        retail_price REAL,
        revenue REAL,
        commission_rate REAL,
        
        -- Passenger Details
        pax_details TEXT,
        total_pax INTEGER,
        
        -- Additional Information
        language TEXT,
        pickup_location TEXT,
        status TEXT,
        
        -- Sync Tracking
        airtable_record_id TEXT,
        synced_to_airtable INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        raw_data TEXT
    )
    '''
    
    def __init__(self, db_path: str = 'headout_bookings.db', logger: Optional[logging.Logger] = None):
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute(self.SCHEMA)
            conn.commit()
            self.logger.info(f'Database initialized: {self.db_path}')
        finally:
            conn.close()
    
    def save_booking(self, booking: Dict) -> Dict:
        """Save or update booking in database"""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO bookings (
                    id, booking_id, agency,
                    customer_name, customer_phone, customer_email,
                    experience_name, experience_id, booking_date, experience_date, time_slot,
                    net_price, retail_price, revenue, commission_rate,
                    pax_details, total_pax,
                    language, pickup_location, status,
                    airtable_record_id, synced_to_airtable,
                    created_at, updated_at, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(booking_id) DO UPDATE SET
                    customer_name=excluded.customer_name,
                    customer_phone=excluded.customer_phone,
                    customer_email=excluded.customer_email,
                    experience_name=excluded.experience_name,
                    experience_id=excluded.experience_id,
                    booking_date=excluded.booking_date,
                    experience_date=excluded.experience_date,
                    time_slot=excluded.time_slot,
                    net_price=excluded.net_price,
                    retail_price=excluded.retail_price,
                    revenue=excluded.revenue,
                    commission_rate=excluded.commission_rate,
                    pax_details=excluded.pax_details,
                    total_pax=excluded.total_pax,
                    language=excluded.language,
                    pickup_location=excluded.pickup_location,
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    raw_data=excluded.raw_data
            ''', (
                booking.get('id'),
                booking.get('booking_id'),
                booking.get('agency', 'Headout'),
                booking.get('customer_name'),
                booking.get('customer_phone'),
                booking.get('customer_email'),
                booking.get('experience_name'),
                booking.get('experience_id'),
                booking.get('booking_date'),
                booking.get('experience_date'),
                booking.get('time_slot'),
                booking.get('net_price'),
                booking.get('retail_price'),
                booking.get('revenue'),
                booking.get('commission_rate'),
                booking.get('pax_details'),
                booking.get('total_pax'),
                booking.get('language'),
                booking.get('pickup_location'),
                booking.get('status'),
                booking.get('airtable_record_id'),
                int(bool(booking.get('synced_to_airtable', 0))),
                booking.get('created_at') or now,
                now,
                json.dumps(booking.get('raw_data', {}))
            ))
            
            conn.commit()
            return {'success': True}
        
        except Exception as e:
            self.logger.error(f'Database save error: {e}')
            return {'success': False, 'error': str(e)}
        
        finally:
            conn.close()
    
    def mark_synced(self, booking_id: str, record_id: Optional[str] = None):
        """Mark booking as synced to Airtable"""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute('''
                UPDATE bookings 
                SET synced_to_airtable=1, airtable_record_id=?
                WHERE booking_id=?
            ''', (record_id, booking_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_unsynced_bookings(self) -> list:
        """Get all bookings that haven't been synced to Airtable"""
        conn = sqlite3.connect(self.db_path)
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM bookings WHERE synced_to_airtable=0')
            return c.fetchall()
        finally:
            conn.close()

    def get_booking(self, booking_id: str) -> Optional[Dict]:
        """Get a single booking by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM bookings WHERE booking_id=?', (booking_id,))
            row = c.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()
