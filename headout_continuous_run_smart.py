import asyncio
import logging
import time
import argparse
import sys
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/headout_continuous_smart.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("continuous_runner")

# CHANGED: Import from smart scraper
from headout_booking_scraper_smart import HeadoutBookingScraper
from headout_config import HeadoutConfig

import json
import os

class StateManager:
    def __init__(self, state_file="scraper_state.json"):
        self.state_file = state_file
        self.state = self.load_state()

    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
        return {"current_page": 0}

    def save_state(self, page_index):
        try:
            self.state["current_page"] = page_index
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_current_page(self):
        return self.state.get("current_page", 0)

    def reset(self):
        self.save_state(0)

async def run_cycle(scraper: HeadoutBookingScraper, pages: int, limit: int, state_manager: StateManager):
    start_page = state_manager.get_current_page()
    logger.info(f"Starting scrape cycle from page {start_page}...")
    
    async def on_page_complete(next_page_index):
        # Save state immediately after a page is processed
        logger.info(f"Page completed. Saving checkpoint: {next_page_index}")
        state_manager.save_state(next_page_index)

    try:
        bookings = await scraper.run_and_sync(
            pages_limit=pages, 
            start_page=start_page, 
            limit=limit,
            on_page_complete=on_page_complete
        )
        
        logger.info(f"Cycle completed. Scraped {len(bookings)} bookings.")
        
        logger.info("Cycle finished successfully. Resetting state to page 0.")
        state_manager.reset()
        
    except Exception as e:
        logger.error(f"Error during scrape cycle: {e}")
        logger.error(traceback.format_exc())
        raise e

async def main():
    parser = argparse.ArgumentParser(description="Headout Continuous Scraper (Smart Sync)")
    parser.add_argument("--interval", type=int, default=300, help="Interval between runs in seconds (default: 300)")
    parser.add_argument("--pages", type=int, default=5, help="Number of pages to scrape per run (default: 5)")
    parser.add_argument("--limit", type=int, default=100, help="Max bookings to scrape per run (default: 100)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (invisible)")
    
    args = parser.parse_args()
    
    logger.info("Initializing Continuous Scraper (Smart Sync)...")
    logger.info(f"Configuration: Interval={args.interval}s, Pages={args.pages}, Limit={args.limit}, Headless={args.headless}")

    # Load config and override headless if requested
    cfg = HeadoutConfig()
    if args.headless:
        cfg.values["BROWSER_HEADLESS"] = "true"
        logger.info("Headless mode ENABLED.")
    
    state_manager = StateManager()

    while True:
        try:
            scraper = HeadoutBookingScraper(cfg=cfg)
            await run_cycle(scraper, args.pages, args.limit, state_manager)
            
            logger.info(f"Sleeping for {args.interval} seconds...")
            await asyncio.sleep(args.interval)
            
        except KeyboardInterrupt:
            logger.info("Stopping scraper (User Interrupt)...")
            break
        except Exception as e:
            logger.error(f"Critical error in main loop: {e}")
            logger.info("Restarting loop in 30 seconds...")
            await asyncio.sleep(30)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
