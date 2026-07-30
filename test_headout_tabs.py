import asyncio
from playwright.async_api import async_playwright
import os

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Load env vars
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
            await page.wait_for_load_state("networkidle")
            await page.wait_for_url("**/dashboard/**", timeout=20000)
            
        await asyncio.sleep(5)
        
        # Dump tabs
        tabs = await page.locator("div[role='tablist'] button, div[role='tablist'] div[role='tab']").all_inner_texts()
        print("Tabs found:", tabs)
        
        # Dump headers
        headers = await page.locator("table thead th").all_inner_texts()
        print("Headers found:", headers)

        await browser.close()

asyncio.run(main())