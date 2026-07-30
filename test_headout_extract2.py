import asyncio
from playwright.async_api import async_playwright
import os
import re

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        from dotenv import load_dotenv
        load_dotenv("headout_config.env")
        email = os.environ.get("HEADOUT_EMAIL")
        password = os.environ.get("HEADOUT_PASSWORD")
        
        await page.goto("https://hub.headout.com/dashboard/bookings/")
        await page.wait_for_load_state("networkidle")
        
        if await page.locator("input[name='email']").count() > 0:
            await page.fill("input[name='email']", email)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            await page.wait_for_url("**/dashboard/**", timeout=20000)
            
        await asyncio.sleep(5)
        tab = page.locator("button, div[role='tab']").filter(has_text=re.compile(r"^By booking date$", re.I)).first
        if await tab.count() > 0:
            await tab.click()
            await asyncio.sleep(5)
            
        body_rows = page.locator("table tbody tr")
        count = await body_rows.count()
        print(f"Count: {count}")
        if count > 0:
            tr = body_rows.nth(0)
            print("Row HTML:", await tr.evaluate("el => el.innerHTML"))
            
            for i in range(1, 13):
                cell = tr.locator(f"td:nth-child({i})")
                try:
                    text = await cell.inner_text()
                    print(f"Col {i}: {text}")
                except Exception as e:
                    print(f"Col {i} Error: {e}")

        await browser.close()

asyncio.run(main())