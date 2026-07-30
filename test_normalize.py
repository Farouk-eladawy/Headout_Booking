from headout_booking_scraper import HeadoutBookingScraper
from headout_config import HeadoutConfig
import asyncio

async def test():
    cfg = HeadoutConfig()
    scraper = HeadoutBookingScraper(cfg)
    row = {
        'row_index': 0,
        'booking_date': 'Jul 30, 2026',
        'experience_date': 'Aug 31, 2026',
        'time_slot': '10:00 AM',
        'booking_id': '33099906',
        'experience_name': 'From Luxor: Half day Karnak Temple and Luxor Temple Tour with Lunch',
        'customer_name': 'TEST TEST',
        'pax_number': '2 Child\n2 Adult',
        'net_price': '$ 193.16',
        'retail_price': '$ 283.80',
        'status': 'SUCCESS',
        'additional_details': 'Pickup Same As Drop Off Location'
    }
    b = scraper._normalize_booking(row)
    print("Normalized:", b)

asyncio.run(test())