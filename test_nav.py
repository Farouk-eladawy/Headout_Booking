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
            await asyncio.sleep(5)
            
        nav = page.locator('nav[aria-label="Pagination Navigation"] button')
        cnt = await nav.count()
        print("Nav buttons:", cnt)
        if cnt == 0:
            nav2 = page.locator('nav button')
            print("Fallback nav buttons:", await nav2.count())
            html = await page.content()
            with open("nav_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
        
        await browser.close()

asyncio.run(main())