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
        
        print("Logging in...")
        await page.goto("https://hub.headout.com/dashboard/bookings/")
        await page.wait_for_load_state("networkidle")
        
        if await page.locator("input[name='email']").count() > 0:
            await page.fill("input[name='email']", email)
            await page.fill("input[name='password']", password)
            await page.click("button[type='submit']")
            await page.wait_for_url("**/dashboard/**", timeout=20000)
            
        await asyncio.sleep(5)
        print("Switching tab...")
        tab = page.locator("button, div[role='tab']").filter(has_text=re.compile(r"^By booking date$", re.I)).first
        if await tab.count() > 0:
            await tab.click()
            await asyncio.sleep(5)
            
        # Try to count rows
        rows = await page.locator("table tbody tr").count()
        print(f"Rows found: {rows}")
        
        if rows > 0:
            # print first row text
            text = await page.locator("table tbody tr").first.inner_text()
            print("First row:", text)
            
            # Print columns
            headers = await page.locator("table thead th").all_inner_texts()
            print("Headers:", headers)
            
        await browser.close()

asyncio.run(main())