import asyncio
import json
import time
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from headout_config import HeadoutConfig
from headout_airtable_smart import HeadoutAirtableManager
from headout_database import HeadoutDatabase


class HeadoutBookingScraper:
    def __init__(self, cfg: Optional[HeadoutConfig] = None):
        self.cfg = cfg or HeadoutConfig()
        self.db = HeadoutDatabase(db_path=self.cfg.get("DATABASE_PATH", "./data/headout_bookings.db"))
        self.airtable = HeadoutAirtableManager(
            api_key=self.cfg.get("AIRTABLE_API_KEY"),
            base_id=self.cfg.get("AIRTABLE_BASE_ID"),
            table_name=self.cfg.get("AIRTABLE_TABLE", "Headout Bookings"),
        )

    async def _select_tab_booking_date(self, page: Page) -> None:
        import logging
        logger = logging.getLogger("scraper_debug")
        logger.info("Attempting to switch to 'By Booking Date' tab...")
        
        try:
            # Wait for tablist to appear
            try:
                await page.wait_for_selector("div[role='tablist']", timeout=10000)
            except Exception:
                pass

            # Try to find the tab by text content specifically
            # Based on screenshot: "By Booking Date"
            tab = page.locator("div[role='tablist'] button, div[role='tablist'] div[role='tab']").filter(has_text="By Booking Date").first
            
            if await tab.count() == 0:
                 # Fallback generic text search
                 tab = page.locator("text='By Booking Date'").first
            
            if await tab.count() > 0:
                # Check if already active
                class_attr = await tab.get_attribute("class") or ""
                aria_selected = await tab.get_attribute("aria-selected")
                
                if "active" in class_attr.lower() or aria_selected == "true":
                    logger.info("'By Booking Date' tab is already active.")
                    return

                logger.info("Clicking 'By Booking Date' tab...")
                await tab.click(force=True)
                
                # Wait for loading state
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                
                # Explicit wait for table reload
                await asyncio.sleep(3.0) 
                logger.info("Tab switch completed.")
                return
            else:
                logger.warning("Could not find 'By Booking Date' tab selector. Dumping page content for debug.")
                # Debug dump
                try:
                    content = await page.content()
                    with open("logs/debug_headless_page.html", "w", encoding="utf-8") as f:
                        f.write(content)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error selecting tab: {e}")
            pass

    async def _set_filters(self, page: Page) -> None:
        await self._select_tab_booking_date(page)

    async def _get_column_indices(self, page: Page) -> Dict[str, int]:
        """Dynamically find column indices based on header text"""
        indices = {
            "booking_date": 2,     # Default fallback
            "experience_date": 3,  # Default fallback
            "time_slot": 4,
            "booking_id": 5,
            "experience_name": 6,
            "customer_name": 7,
            "pax_number": 8,
            "net_price": 9,
            "retail_price": 10,
            "status": 11,
            "additional_details": 12
        }
        
        try:
            # Get all header cells
            headers = page.locator("table thead th")
            count = await headers.count()
            
            if count == 0:
                return indices

            for i in range(count):
                text = (await headers.nth(i).inner_text() or "").lower().strip()
                idx = i + 1 # nth-child is 1-based
                
                if "booking date" in text:
                    indices["booking_date"] = idx
                elif "experience date" in text or "travel date" in text or "tour date" in text:
                    indices["experience_date"] = idx
                elif "time" in text:
                    indices["time_slot"] = idx
                elif "booking ref" in text or "booking id" in text or "reference" in text:
                    indices["booking_id"] = idx
                elif "experience" in text and "date" not in text: # Avoid matching Experience Date
                    indices["experience_name"] = idx
                elif "customer" in text or "guest" in text or "traveler" in text:
                    indices["customer_name"] = idx
                elif "pax" in text or "participants" in text:
                    indices["pax_number"] = idx
                elif "net" in text and "price" in text:
                    indices["net_price"] = idx
                elif "retail" in text or "total" in text:
                    indices["retail_price"] = idx
                elif "status" in text:
                    indices["status"] = idx
                elif "details" in text or "additional" in text:
                    indices["additional_details"] = idx
            
            import logging
            logger = logging.getLogger("scraper_debug")
            logger.info(f"Detected column indices: {indices}")
            
        except Exception as e:
            pass
            
        return indices

    async def _extract_rows(self, page: Page) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        
        # Dynamically get indices
        col_idx = await self._get_column_indices(page)
        
        body_rows = page.locator("table tbody tr")
        count = await body_rows.count()
        for i in range(count):
            tr = body_rows.nth(i)
            async def cell_text(n: int) -> str:
                try:
                    cell = tr.locator(f"td:nth-child({n})")
                    return ((await cell.inner_text()) or "").strip()
                except Exception:
                    return ""
            rows.append({
                "row_index": i,
                "booking_date": await cell_text(col_idx["booking_date"]),
                "experience_date": await cell_text(col_idx["experience_date"]),
                "time_slot": await cell_text(col_idx["time_slot"]),
                "booking_id": await cell_text(col_idx["booking_id"]),
                "experience_name": await cell_text(col_idx["experience_name"]),
                "customer_name": await cell_text(col_idx["customer_name"]),
                "pax_number": await cell_text(col_idx["pax_number"]),
                "net_price": await cell_text(col_idx["net_price"]),
                "retail_price": await cell_text(col_idx["retail_price"]),
                "status": await cell_text(col_idx["status"]),
                "additional_details": await cell_text(col_idx["additional_details"]),
            })
        return rows

    def _normalize_booking(self, row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        import re
        booking_id = (row.get("booking_id") or "").strip()
        if not booking_id:
            blob = " ".join(str(v) for v in row.values() if v)
            m = re.search(r"\b(\d{6,})\b", blob)
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

        def parse_pax(s: Optional[str]) -> (str, Optional[int]):
            if not s:
                return "", None
            parts = []
            total = 0
            for m in re.finditer(r"(\d+)\s*(Adult|Child|Student|Infant|General|Senior)", s or "", re.I):
                c = int(m.group(1))
                t = m.group(2).capitalize()
                parts.append(f"{t}:{c}")
                total += c
            return (", ".join(parts) if parts else s.strip(), total if total > 0 else None)

        pax_details, total_pax = parse_pax(row.get("pax_number"))
        net_price = parse_currency(row.get("net_price"))
        retail_price = parse_currency(row.get("retail_price"))

        language = None
        pickup = None
        customer_email = None
        customer_phone = None
        
        add = row.get("additional_details") or ""
        
        mm = re.search(r"Language:\s*([^\n]+)", add)
        if mm:
            language = mm.group(1).strip()
        mm = re.search(r"Pickup Location:\s*([^\n]+)", add)
        if mm:
            pickup = mm.group(1).strip()
            
        # Try to extract Email/Phone from Additional Details directly
        mm = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", add, re.I)
        if mm:
            customer_email = mm.group(1).strip()
            
        mm = re.search(r"Phone:\s*(\+?\d[\d\s()-]{6,}\d)", add, re.I)
        if mm:
            customer_phone = mm.group(1).strip()

        # Experience title and option (subtitle)
        exp_text = (row.get("experience_name") or "").strip()
        exp_lines = [ln.strip() for ln in exp_text.splitlines() if ln.strip()]
        main_title = exp_lines[0] if exp_lines else (exp_text or None)
        option = exp_lines[1] if len(exp_lines) > 1 else None

        return {
            "id": booking_id,
            "booking_id": booking_id,
            "booking_date": (row.get("booking_date") or "").strip() or None,
            "experience_date": (row.get("experience_date") or "").strip() or None,
            "time_slot": (row.get("time_slot") or "").strip() or None,
            "experience_name": main_title,
            "option": option,
            "customer_name": (row.get("customer_name") or "").strip() or None,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "pax_details": pax_details or None,
            "total_pax": total_pax,
            "net_price": net_price,
            "retail_price": retail_price,
            "status": (row.get("status") or "").strip() or None,
            "language": language,
            "pickup_location": pickup,
        }

    async def _augment_contact_details(self, page: Page, row_index: int, booking: Dict[str, Any]) -> None:
        import re
        import logging
        logger = logging.getLogger("scraper_debug")
        
        # If we already have email AND phone from additional_details, no need to click
        if booking.get("customer_email") and booking.get("customer_phone"):
            return

        # Ensure clean state (close any previous dialogs)
        try:
            await page.keyboard.press('Escape')
            await asyncio.sleep(0.5)
        except:
            pass
        
        status = (booking.get("status") or "").lower()
        is_cancelled = "cancel" in status or "decline" in status

        try:
            # Re-locate row by ID first if possible to ensure we hit the right row
            # But we don't have a reliable selector for TR by ID unless we search text
            # We will use row_index but with extra care
            tr = page.locator("table tbody tr").nth(row_index)
            
            # Double check if this TR actually contains our Booking ID to prevent row-shifting errors
            row_text = await tr.inner_text()
            if booking.get("booking_id") not in row_text:
                # logger.warning(f"Row mismatch! Expected ID {booking.get('booking_id')} not found in row {row_index}. Skipping click.")
                return

            # STRATEGY: Try to extract from row text FIRST (before clicking)
            # This covers cases where email/phone is visible in "Additional Details" column even for cancelled bookings
            m_email_row = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", row_text, re.I)
            m_phone_row = re.search(r"Phone:\s*(\+?\d[\d\s()-]{6,}\d)", row_text, re.I)
            
            if m_email_row and not booking.get("customer_email"):
                booking["customer_email"] = m_email_row.group(1)
            
            if m_phone_row and not booking.get("customer_phone"):
                booking["customer_phone"] = m_phone_row.group(1)
                
            # If we found both, we are done
            if booking.get("customer_email") and booking.get("customer_phone"):
                return

            # If cancelled, do NOT attempt to click button (it likely doesn't exist or work)
            if is_cancelled:
                return

            # Find button
            btn = tr.locator('button').filter(has_text="View contact details").first
            
            try:
                # Wait up to 3 seconds for button to appear
                await btn.wait_for(state="attached", timeout=3000)
            except:
                # Fallback to span
                btn = tr.locator('span').filter(has_text="View contact details").first
                try:
                    await btn.wait_for(state="attached", timeout=2000)
                except:
                    # Scroll and try again
                    try:
                        await tr.scroll_into_view_if_needed()
                        btn = tr.locator('button, span').filter(has_text="View contact details").first
                        if await btn.count() == 0:
                            return
                    except:
                        return

            # Click
            if await btn.is_visible():
                await btn.click()
            else:
                await btn.evaluate("el => el.click()")
            
            # Wait for dialog
            try:
                await page.wait_for_selector("text=Email:", timeout=5000)
            except:
                pass
            
            await asyncio.sleep(1.0)
            
            # Get text AFTER click
            
            # 1. Check Row Text (if inline expansion)
            text_after = await tr.inner_text()
            m_email = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", text_after, re.I)
            m_phone = re.search(r"Phone:\s*(\+?\d[\d\s()-]{6,}\d)", text_after, re.I)
            
            # 2. If not in row, check for VISIBLE Dialog/Container
            if not m_email and not m_phone:
                 locator = page.locator("div, section, article").filter(has_text=re.compile(r"Email:", re.I))
                 count = await locator.count()
                 
                 target_text = ""
                 for i in range(count - 1, -1, -1):
                     el = locator.nth(i)
                     if await el.is_visible():
                         # Validation: Check if this dialog belongs to the current booking
                         dialog_text = await el.inner_text()
                         
                         # CRITICAL SAFETY: Ignore large containers (like the whole page or table wrapper)
                         # A contact card is small (usually < 500-1000 chars). 
                         # If we match the whole table, we might find the correct ID (in row) AND a wrong email (in another dialog).
                         if len(dialog_text) > 1000:
                             continue

                         booking_id = booking.get("booking_id")
                         customer_name = booking.get("customer_name")
                         
                         is_match = False
                         if booking_id and booking_id in dialog_text:
                             is_match = True
                         elif customer_name and customer_name in dialog_text:
                             is_match = True
                         
                         if is_match:
                             target_text = dialog_text
                             break
                         else:
                             pass
                 
                 if target_text:
                     m_email = re.search(r"Email:\s*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", target_text, re.I)
                     m_phone = re.search(r"Phone:\s*(\+?\d[\d\s()-]{6,}\d)", target_text, re.I)

            if m_email:
                if not booking.get("customer_email"):
                    booking["customer_email"] = m_email.group(1)
            
            if m_phone:
                if not booking.get("customer_phone"):
                    booking["customer_phone"] = m_phone.group(1)
            
            # Close dialog
            await page.keyboard.press('Escape')
            
        except Exception as e:
            pass

    async def _login_if_needed(self, page: Page) -> None:
        import logging
        logger = logging.getLogger("scraper_debug")
        
        # Check if we are on login page
        # URL contains 'login' or explicit login form presence
        if "login" in page.url.lower() or await page.locator("input[name='email']").count() > 0:
            logger.info("Login page detected. Attempting to log in...")
            
            email = self.cfg.email
            password = self.cfg.password
            
            if not email or not password:
                logger.error("Credentials not found in config! Cannot login.")
                return

            try:
                # Fill email
                await page.fill("input[name='email']", email)
                
                # Fill password
                await page.fill("input[name='password']", password)
                
                # Click Sign In
                # Based on debug html: button[data-qa-marker="Sign in"]
                btn = page.locator("button[data-qa-marker='Sign in']")
                if await btn.count() > 0:
                    await btn.click()
                else:
                    await page.click("button[type='submit']")
                
                logger.info("Credentials submitted. Waiting for navigation...")
                await page.wait_for_load_state("networkidle")
                
                # Wait for dashboard specific element
                try:
                    await page.wait_for_url("**/dashboard/**", timeout=20000)
                    logger.info("Successfully logged in.")
                except Exception:
                    logger.warning("Login might have failed or redirect is slow. Current URL: " + page.url)
                    
            except Exception as e:
                logger.error(f"Login failed: {e}")

    async def scrape(self, pages_limit: int = 2, start_page: int = 0, limit: Optional[int] = 20, on_batch_processed: Optional[Any] = None, on_page_complete: Optional[Any] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        async with async_playwright() as p:
            bt = getattr(p, self.cfg.browser_engine)
            context: BrowserContext = await bt.launch_persistent_context(
                user_data_dir=self.cfg.user_data_dir,
                channel=self.cfg.browser_channel,
                headless=self.cfg.headless,
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            dests = [
                self.cfg.portal_url or "",
                "https://hub.headout.com/dashboard/bookings/",
            ]
            for d in dests:
                if not d:
                    continue
                try:
                    await page.goto(d, timeout=60000)
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)  # Extra wait for dynamic elements
                    break
                except Exception:
                    continue
            
            # Check login
            await self._login_if_needed(page)

            await self._set_filters(page)
            
            # Navigate to start_page if > 0
            current_page = 0
            if start_page > 0:
                import logging
                logger = logging.getLogger("scraper_debug")
                logger.info(f"Resuming from page {start_page}...")
                
                for _ in range(start_page):
                    try:
                        nav = page.locator('nav[aria-label="Pagination Navigation"] button')
                        cnt = await nav.count()
                        if cnt > 0:
                            await nav.last.click() 
                            await page.wait_for_load_state("networkidle")
                            await asyncio.sleep(1.0)
                        else:
                            logger.warning("Pagination controls not found during skip.")
                            break
                    except Exception as e:
                        logger.warning(f"Error skipping to page: {e}")
                        break
                current_page = start_page

            page_index = 0 # Relative index for the loop limit
            
            # lightweight progress bar without hard dependency
            try:
                from tqdm import tqdm  # type: ignore
                pbar = tqdm(total=limit or 0, disable=not bool(limit))
            except Exception:
                class _P:
                    def update(self, n):
                        pass
                    def close(self):
                        pass
                pbar = _P()
            
            while page_index < pages_limit and (limit is None or len(results) < limit):
                # Ensure table is loaded
                try:
                    await page.wait_for_selector("table tbody tr", timeout=10000)
                except Exception:
                    pass
                
                rows = await self._extract_rows(page)
                
                # New: Batch List for this page
                current_page_bookings = []
                
                for r in rows:
                    b = self._normalize_booking(r)
                    if not b:
                        continue
                    await self._augment_contact_details(page, r.get("row_index", 0), b)
                    results.append(b)
                    current_page_bookings.append(b)
                    
                    if limit is not None:
                        pbar.update(1)
                    if limit is not None and len(results) >= limit:
                        break
                
                # Process batch immediately if callback provided
                if on_batch_processed and current_page_bookings:
                    await on_batch_processed(current_page_bookings)
                
                # Notify page completion
                if on_page_complete:
                    await on_page_complete(current_page + 1) # Next page index to start from
                
                # Check limit again to break outer loop if needed
                if limit is not None and len(results) >= limit:
                    break

                try:
                    nav = page.locator('nav[aria-label="Pagination Navigation"] button')
                    cnt = await nav.count()
                    if cnt > 0:
                        next_btn = page.locator('button[aria-label="Go to next page"], button[aria-label="Next page"], button[title="Next page"]')
                        if await next_btn.count() > 0:
                            await next_btn.first.click()
                        else:
                            # Fallback
                            next_text_btn = page.locator('button:has-text(">"), button:has-text("Next")').last
                            if await next_text_btn.count() > 0:
                                await next_text_btn.click()
                            else:
                                await nav.last.click()

                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(5)  # INCREASED WAIT: Allocated time for page transition
                    else:
                        break
                except Exception:
                    break
                page_index += 1
                current_page += 1

            pbar.close()
            try:
                await context.close()
            except Exception:
                pass
        return results

    async def run_and_sync(self, pages_limit: int = 2, start_page: int = 0, limit: int = 20, on_page_complete: Optional[Any] = None) -> List[Dict[str, Any]]:
        # Define callback to process bookings page-by-page
        async def process_batch(batch: List[Dict[str, Any]]):
            import logging
            logger = logging.getLogger("scraper_debug")
            logger.info(f"Processing batch of {len(batch)} bookings...")
            
            for b in batch:
                # Idempotency Check
                # 1. Fetch existing booking from DB
                existing = self.db.get_booking(b['booking_id'])
                
                changed_keys = None
                
                if existing:
                    # Determine changed keys
                    changed_keys = []
                    # List of keys we care about syncing
                    keys_to_check = [
                        'status',
                        'experience_date',
                        'time_slot',
                        'pax_details',
                        'total_pax',
                        'net_price',
                        'retail_price',
                        'customer_name',
                        'customer_phone',
                        'customer_email',
                        'pickup_location',
                        'language',
                        'experience_name',
                        'option'
                    ]
                    
                    def norm(v): return str(v or "").strip()
                    
                    for k in keys_to_check:
                        if norm(existing.get(k)) != norm(b.get(k)):
                            changed_keys.append(k)
                    
                    if not changed_keys:
                        # No changes detected
                        # We pass empty list to upsert_booking, which tells it to "Ensure Exists Only"
                        pass
                    else:
                        logger.info(f"Changes detected for {b['booking_id']}: {changed_keys}")
                else:
                    # New booking -> None implies Full Sync
                    changed_keys = None
                    logger.info(f"New booking {b['booking_id']} detected.")

                # Always save to DB (it handles ON CONFLICT updates efficiently)
                self.db.save_booking(b)
                
                # Smart Sync
                res = self.airtable.upsert_booking(b, changed_keys=changed_keys)
                
                if res.get("success"):
                    self.db.mark_synced(b.get("booking_id"), res.get("recordid"))
                    if res.get("action") == "updated":
                        logger.info(f"Synced changes for {b['booking_id']}")
                    elif res.get("action") == "skipped_no_changes":
                        pass
            
            logger.info("Batch processing completed.")

        return await self.scrape(
            pages_limit=pages_limit, 
            start_page=start_page,
            limit=limit, 
            on_batch_processed=process_batch,
            on_page_complete=on_page_complete
        )

    def export_to_json(self, data: List[Dict[str, Any]], filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        import csv
        if not data:
            with open(filename, "w", encoding="utf-8", newline="") as f:
                pass
            return
        keys = [
            "id","booking_id","booking_date","experience_date","time_slot",
            "experience_name","option","customer_name","customer_email","customer_phone",
            "pax_details","total_pax","net_price","retail_price","status","language","pickup_location"
        ]
        with open(filename, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for row in data:
                w.writerow({k: row.get(k) for k in keys})

    def export_to_excel(self, data: List[Dict[str, Any]], filename: str) -> None:
        try:
            from openpyxl import Workbook
        except Exception:
            return
        wb = Workbook()
        ws = wb.active
        if not data:
            wb.save(filename)
            return
        headers = [
            "id","booking_id","booking_date","experience_date","time_slot",
            "experience_name","option","customer_name","customer_email","customer_phone",
            "pax_details","total_pax","net_price","retail_price","status","language","pickup_location"
        ]
        ws.append(headers)
        for row in data:
            ws.append([row.get(h) for h in headers])
        wb.save(filename)
