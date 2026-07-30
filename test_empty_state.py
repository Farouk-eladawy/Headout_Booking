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
        await page.goto("https://hub.headout.com/dashboard/bookings/")
        await page.wait_for_load_state("networkidle")
        if await page.locator("input[name='email']").count() > 0:
            await page.fill("input[name='email']", os.environ.get("HEADOUT_EMAIL"))
            await page.fill("input[name='password']", os.environ.get("HEADOUT_PASSWORD"))
            await page.click("button[type='submit']")
            await page.wait_for_url("**/dashboard/**", timeout=20000)
            
        await asyncio.sleep(5)
        tab = page.locator("button, div[role='tab']").filter(has_text=re.compile(r"^By booking date$", re.I)).first
        if await tab.count() > 0:
            await tab.click()
            
            # DON'T WAIT, check what tr is there immediately!
            try:
                await page.wait_for_selector("table tbody tr", timeout=2000)
                rows = await page.locator("table tbody tr").count()
                print("Rows immediately after click:", rows)
                if rows > 0:
                    print("Row HTML:", await page.locator("table tbody tr").first.inner_html())
            except Exception as e:
                print("No tr found immediately.")
                
            await asyncio.sleep(5)
            rows = await page.locator("table tbody tr").count()
            print("Rows after 5s:", rows)

        await browser.close()

asyncio.run(main())