import re
from typing import List, Dict, Optional, Tuple

from playwright.async_api import async_playwright, Page
from headout_config import HeadoutConfig


async def _try_navigate(page: Page, urls: List[str]) -> Optional[str]:
    for url in urls:
        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_load_state("networkidle")
            return url
        except Exception:
            continue
    return None


async def _extract_rows(page: Page) -> List[Dict]:
    rows: List[Dict] = []
    body_rows = page.locator("table tbody tr")
    count = await body_rows.count()
    for i in range(count):
        tr = body_rows.nth(i)
        async def cell(n: int) -> str:
            try:
                txt = tr.locator(f"td:nth-child({n})")
                return ((await txt.inner_text()) or "").strip()
            except Exception:
                return ""
        row = {
            "row_index": i,
            "booking_date": await cell(2),
            "experience_date": await cell(3),
            "time_slot": await cell(4),
            "booking_id": await cell(5),
            "experience_name": await cell(6),
            "customer_name": await cell(7),
            "pax_number": await cell(8),
            "net_price": await cell(9),
            "retail_price": await cell(10),
            "status": await cell(11),
            "additional_details": await cell(12),
        }
        rows.append(row)
    return rows


def _row_to_booking(row: Dict) -> Optional[Dict]:
    booking_id = (row.get("booking_id") or "").strip()
    if not booking_id:
        # fallback regex
        text_blob = " ".join(str(v) for v in row.values() if v)
        m = re.search(r"\b([0-9]{6,})\b", text_blob)
        booking_id = m.group(1) if m else None
    if not booking_id:
        return None

    def parse_currency(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        try:
            s2 = re.sub(r"[^0-9.,-]", "", s)
            s2 = s2.replace(",", "")
            return float(s2) if s2 else None
        except Exception:
            return None

    def parse_pax(s: Optional[str]) -> Tuple[str, Optional[int]]:
        if not s:
            return "", None
        parts = []
        total = 0
        for m in re.finditer(r"(\d+)\s*(Adult|Child|Student|Infant|Senior)", s, re.I):
            count = int(m.group(1))
            cat = m.group(2).capitalize()
            parts.append(f"{cat}:{count}")
            total += count
        return (", ".join(parts) if parts else s.strip(), total if total > 0 else None)

    pax_details, total_pax = parse_pax(row.get("pax_number"))
    net_price = parse_currency(row.get("net_price"))
    retail_price = parse_currency(row.get("retail_price"))

    language = None
    pickup = None
    add = row.get("additional_details") or ""
    mm = re.search(r"Language:\s*([^\n]+)", add)
    if mm:
        language = mm.group(1).strip()
    mm = re.search(r"Pickup Location:\s*([^\n]+)", add)
    if mm:
        pickup = mm.group(1).strip()

    booking = {
        "id": booking_id,
        "booking_id": booking_id,
        "customer_name": (row.get("customer_name") or "").strip() or None,
        "experience_name": (row.get("experience_name") or "").strip() or None,
        "booking_date": (row.get("booking_date") or "").strip() or None,
        "experience_date": (row.get("experience_date") or "").strip() or None,
        "time_slot": (row.get("time_slot") or "").strip() or None,
        "status": (row.get("status") or "").strip() or None,
        "pax_details": pax_details or None,
        "total_pax": total_pax,
        "net_price": net_price,
        "retail_price": retail_price,
        "language": language,
        "pickup_location": pickup,
    }
    return booking


async def scrape_recent_bookings_async(limit: int = 5, pages_limit: int = 1) -> List[Dict]:
    cfg = HeadoutConfig()
    urls: List[str] = []
    if cfg.portal_url:
        urls.append(cfg.portal_url)
    urls += [
        "https://hub.headout.com/dashboard/bookings/",
        "https://hub.headout.com/bookings",
        "https://partners.headout.com/bookings",
    ]
    results: List[Dict] = []
    async with async_playwright() as p:
        bt = getattr(p, cfg.browser_engine)
        context = await bt.launch_persistent_context(
            user_data_dir=cfg.user_data_dir,
            channel=cfg.browser_channel,
            headless=cfg.headless,
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        dest = await _try_navigate(page, urls)
        if not dest:
            await context.close()
            return results
        try:
            await select_by_booking_date_tab(page)
        except Exception:
            pass
        page_index = 0
        while page_index < pages_limit and (limit is None or len(results) < limit):
            rows = await _extract_rows(page)
            for r in rows:
                b = _row_to_booking(r)
                if b:
                    # augment contact details if available
                    try:
                        tr = page.locator("table tbody tr").nth(r.get("row_index", 0))
                        btn = tr.locator('button:has-text("View contact details")').first
                        if await btn.count() > 0:
                            await btn.click()
                            dialog = page.locator('[role="dialog"]').first
                            if await dialog.count() > 0:
                                txt = (await dialog.inner_text()) or ""
                                m_email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", txt)
                                m_phone = re.search(r"\+?\d[\d\s()-]{6,}\d", txt)
                                if m_email and not b.get("customer_email"):
                                    b["customer_email"] = m_email.group(0)
                                if m_phone and not b.get("customer_phone"):
                                    b["customer_phone"] = m_phone.group(0)
                            # attempt close dialog
                            try:
                                close_btn = page.locator('[role="dialog"] button:has-text("Close")').first
                                if await close_btn.count() > 0:
                                    await close_btn.click()
                                else:
                                    await page.keyboard.press('Escape')
                            except Exception:
                                pass
                    except Exception:
                        pass
                    results.append(b)
                if limit is not None and len(results) >= limit:
                    break
            # go next page if available
            try:
                nav = page.locator('nav[aria-label="Pagination Navigation"] button')
                count = await nav.count()
                # find current page and click next
                if count > 0:
                    # heuristic: click the last visible numbered button not currently active
                    await nav.nth(min(page_index + 1, count - 1)).click()
                    await page.wait_for_load_state("networkidle")
            except Exception:
                break
            page_index += 1
        await context.close()
    return results

async def select_by_booking_date_tab(page: Page) -> None:
    try:
        tab = page.getByRole('tab', name='By Booking Date')
        if await tab.count() > 0:
            await tab.first.click()
            await page.wait_for_load_state('networkidle')
            return
    except Exception:
        pass
    try:
        btn = page.locator("button[role='tab']").filter(has_text="By Booking Date")
        if await btn.count() > 0:
            await btn.first.click()
            await page.wait_for_load_state('networkidle')
    except Exception:
        pass

