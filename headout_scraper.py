import asyncio
import logging
import sys
import os
from typing import Dict, List, Optional

from headout_config import HeadoutConfig
from headout_database import HeadoutDatabase
from headout_airtable import HeadoutAirtableManager
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

class HeadoutScraper:
    def __init__(self):
        self.config = HeadoutConfig()
        self.logger = logging.getLogger("HeadoutScraper")
        
        # Ensure data directory exists
        db_path = self.config.get("DATABASE_PATH", "./data/headout_bookings.db")
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
        # Initialize DB
        self.db = HeadoutDatabase(db_path=db_path, logger=self.logger)
        
        # Initialize Airtable
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

    async def sync_booking(self, booking: Dict) -> bool:
        self.logger.info(f"Syncing {booking.get('booking_id')}...")
        
        db_result = self.db.save_booking(booking)
        if not db_result.get('success'):
            self.logger.error(f"DB save failed: {db_result.get('error')}")
            return False
        
        at_result = self.airtable.upsert_booking(booking)
        if at_result.get('success'):
            self.db.mark_synced(booking.get('booking_id'), at_result.get('recordid'))
            self.logger.info(f"Synced: {booking.get('booking_id')}")
            return True
        else:
            self.logger.error(f"Airtable failed: {at_result}")
            return False

    async def run_test_cycle(self):
        """Runs a single test cycle: Login -> Mock Booking -> DB -> Airtable"""
        self.logger.info("Starting System Test Cycle")
        
        # 1. Login
        if not self.login():
            self.logger.error("Aborting test cycle due to login failure")
            return
            
        # 2. CSV import if provided
        csv_path = self.config.csv_path
        real = []
        if csv_path and os.path.exists(csv_path):
            try:
                real = parse_headout_csv(csv_path)
                self.logger.info(f"Found {len(real)} bookings from CSV to sync")
            except Exception as e:
                self.logger.error(f"CSV import failed: {e}")
                real = []

        # 3. Try real bookings scrape if none from CSV
        if not real:
            real = await scrape_recent_bookings_async(limit=10, pages_limit=2)
        if real:
            self.logger.info(f"Found {len(real)} real bookings to sync")
            for b in real:
                await self.sync_booking(b)
        else:
            # 4. Fallback to mock data
            import uuid
            from datetime import datetime
            mock_id = f"TEST-RUN-{uuid.uuid4().hex[:6].upper()}"
            mock_booking = {
                "id": mock_id,
                "booking_id": mock_id,
                "customer_name": "System Tester",
                "experience_name": "System Integrity Check",
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
    scraper = HeadoutScraper()
    asyncio.run(scraper.run_test_cycle())
