import asyncio
import logging
import os
import argparse
from datetime import datetime

from headout_booking_scraper import HeadoutBookingScraper
from headout_config import HeadoutConfig


def setup_logging(log_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


async def main():
    cfg = HeadoutConfig()
    setup_logging(cfg.get('LOG_FILE', './logs/headout_full_scrape.log'))
    scraper = HeadoutBookingScraper(cfg)

    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', type=int, default=int(os.getenv('PAGES_LIMIT', '5')))
    parser.add_argument('--limit', type=int, default=int(os.getenv('TOTAL_LIMIT', '100')))
    args = parser.parse_args()
    pages_limit = args.pages
    per_total = args.limit
    logging.info(f"Starting full scrape: pages_limit={pages_limit}, total_limit={per_total}")
    data = await scraper.run_and_sync(pages_limit=pages_limit, limit=per_total)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = './data'
    os.makedirs(out_dir, exist_ok=True)
    csv_file = os.path.join(out_dir, f'bookings_export_{ts}.csv')
    xlsx_file = os.path.join(out_dir, f'bookings_export_{ts}.xlsx')
    scraper.export_to_csv(data, csv_file)
    scraper.export_to_excel(data, xlsx_file)
    logging.info(f"Exported: {csv_file} and {xlsx_file}")


if __name__ == '__main__':
    asyncio.run(main())
