import asyncio
import logging
import sys
import os
from typing import Dict, List, Optional

from headout_config import HeadoutConfig
from headout_database import HeadoutDatabase
# CHANGED: Import from smart version
from headout_airtable_smart import HeadoutAirtableManager
from headout_login import ensure_session
from headout_scrape import scrape_recent_bookings_async
from headout_import_csv import parse_headout_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class HeadoutScraperSmart:
    def __init__(self):
        self.config = HeadoutConfig()
        self.logger = logging.getLogger("HeadoutScraperSmart")
        
        # Ensure data directory exists
        db_path = self.config.get("DATABASE_PATH", "./data/headout_bookings.db")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Initialize DB
        self.db = HeadoutDatabase(db_path=db_path, logger=self.logger)
        
        # Initialize Airtable (Smart)
        self.airtable = HeadoutAirtableManager(
            api_key=self.config.get("AIRTABLE_API_KEY"),
            base_id=self.config.get("AIRTABLE_BASE_ID"),
            table_name=self.config.get("AIRTABLE_TABLE", "Headout Bookings"),
            logger=self.logger
        )

    def login(self):
        self.logger.info("Initiating login process...")
        try:
            session_path = ensure_session(self.config)
            self.logger.info(f"Login successful. Session stored at: {session_path}")
            return True
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def _compare_bookings(self, old: Dict, new: Dict) -> List[str]:
        """
        Compare old and new booking to find changed keys.
        Returns list of keys that changed.
        """
        changed = []
        
        # List of keys we care about syncing
        # Note: These must match Headout dict keys
        keys_to_check = [
            'status',
            'experience_date',
            'time_slot',
            'pax_details',
            'total_pax',
            'net_price',
            'retail_price',
            'customer_name',
            'customer_phone',
            'customer_email',
            'pickup_location',
            'language',
            'experience_name',
            'option'
        ]
        
        for key in keys_to_check:
            old_val = old.get(key)
            new_val = new.get(key)
            
            # Normalize for comparison
            if old_val is None: old_val = ""
            if new_val is None: new_val = ""
            
            if str(old_val).strip() != str(new_val).strip():
                changed.append(key)
                
        return changed

    async def sync_booking(self, booking: Dict) -> bool:
        b_id = booking.get('booking_id')
        self.logger.info(f"Syncing {b_id}...")
        
        # 1. Get previous state from DB
        existing_booking = self.db.get_booking(b_id)
        
        # 2. Determine changed keys
        changed_keys = None
        if existing_booking:
            changed_keys = self._compare_bookings(existing_booking, booking)
            if not changed_keys:
                self.logger.info(f"No changes detected in Headout for {b_id}. Will check Airtable existence but skip update.")
            else:
                self.logger.info(f"Changes detected for {b_id}: {changed_keys}")
        else:
            self.logger.info(f"New booking {b_id} detected. Full sync.")

        # 3. Save to Local DB (Always update local to match Headout)
        db_result = self.db.save_booking(booking)
        if not db_result.get('success'):
            self.logger.error(f"DB save failed: {db_result.get('error')}")
            return False
        
        # 4. Sync to Airtable (Smart)
        # Pass changed_keys to upsert_booking
        at_result = self.airtable.upsert_booking(booking, changed_keys=changed_keys)
        
        if at_result.get('success'):
            self.db.mark_synced(b_id, at_result.get('recordid'))
            action = at_result.get('action', 'synced')
            self.logger.info(f"Airtable Result: {action} for {b_id}")
            return True
        else:
            self.logger.error(f"Airtable failed: {at_result}")
            return False

    async def run_test_cycle(self):
        """Runs a single test cycle: Login -> Mock Booking -> DB -> Airtable"""
        self.logger.info("Starting System Test Cycle (Smart Sync)")
        
        if not self.login():
            self.logger.error("Aborting test cycle due to login failure")
            return
            
        csv_path = self.config.csv_path
        real = []
        if csv_path and os.path.exists(csv_path):
            try:
                real = parse_headout_csv(csv_path)
                self.logger.info(f"Found {len(real)} bookings from CSV to sync")
            except Exception as e:
                self.logger.error(f"CSV import failed: {e}")
                real = []

        if not real:
            real = await scrape_recent_bookings_async(limit=10, pages_limit=2)
            
        if real:
            self.logger.info(f"Found {len(real)} real bookings to sync")
            for b in real:
                await self.sync_booking(b)
        else:
            # Mock data for testing
            import uuid
            from datetime import datetime
            mock_id = f"TEST-SMART-{uuid.uuid4().hex[:6].upper()}"
            mock_booking = {
                "id": mock_id,
                "booking_id": mock_id,
                "customer_name": "Smart Sync Tester",
                "experience_name": "Integrity Check",
                "booking_date": datetime.now().isoformat(),
                "status": "Test",
                "total_pax": 1,
                "net_price": 0,
                "revenue": 0
            }
            self.logger.info(f"Generated mock booking: {mock_id}")
            await self.sync_booking(mock_booking)
        
        self.logger.info("Test Cycle Complete")

if __name__ == "__main__":
    scraper = HeadoutScraperSmart()
    asyncio.run(scraper.run_test_cycle())
