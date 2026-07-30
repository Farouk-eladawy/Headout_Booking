import asyncio
from headout_booking_scraper import HeadoutBookingScraper
from headout_config import HeadoutConfig
import logging

async def main():
    logging.basicConfig(level=logging.INFO)
    cfg = HeadoutConfig()
    scraper = HeadoutBookingScraper(cfg)
    
    async def on_batch(batch):
        print("BATCH PROCESSED:", len(batch))
        
    await scraper.scrape(pages_limit=1, limit=200, on_batch_processed=on_batch)

asyncio.run(main())