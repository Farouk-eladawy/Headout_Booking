"""Force-repair specific Headout bookings in Airtable from the live Hub table."""

import argparse
import asyncio
import logging
import os

from headout_booking_scraper import HeadoutBookingScraper
from headout_config import HeadoutConfig
from headout_run_full_scrape import setup_logging

DEFAULT_IDS = [
    "34047530",
    "34087341",
    "34069882",
    "34042411",
    "33779837",
    "34064002",
    "34054650",
    "34054742",
    "34051498",
    "34042668",
    "33833737",
    "34098581",
    "34098642",
    "34091097",
    "34078651",
    "34066977",
    "34054438",
    "33703759",
    "34101716",
    "34077864",
    "33802215",
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("booking_ids", nargs="*", default=DEFAULT_IDS)
    args = parser.parse_args()

    cfg = HeadoutConfig()
    cfg.values["BROWSER_HEADLESS"] = "true"
    setup_logging(cfg.get("LOG_FILE", "./logs/headout_repair.log"))
    scraper = HeadoutBookingScraper(cfg)
    report = await scraper.repair_booking_ids(args.booking_ids)
    logging.info("Repair report: %s", report)
    print(report)


if __name__ == "__main__":
    os.environ.setdefault("BROWSER_HEADLESS", "true")
    asyncio.run(main())
