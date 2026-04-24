import os
import json
import time
from typing import Optional

from playwright.sync_api import sync_playwright, BrowserContext, Page

from headout_config import HeadoutConfig


def _visible(page: Page, selector: str) -> bool:
    try:
        loc = page.locator(selector)
        return loc.first.is_visible()
    except Exception:
        return False


def _fill_if_exists(page: Page, selector: str, value: str) -> bool:
    try:
        loc = page.locator(selector)
        if loc.first.count() > 0:
            loc.first.fill(value)
            return True
    except Exception:
        pass
    return False


def attempt_credential_login(page: Page, email: str, password: str) -> bool:
    email_selectors = [
        "input[name='email']",
        "#email",
        "input[type='email']",
        "input[autocomplete='email']",
    ]
    password_selectors = [
        "input[name='password']",
        "#password",
        "input[type='password']",
        "input[autocomplete='current-password']",
    ]
    submit_selectors = [
        "button[type='submit']",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "text=Sign in",
        "text=Log in",
    ]

    email_filled = any(_fill_if_exists(page, s, email) for s in email_selectors)
    pwd_filled = any(_fill_if_exists(page, s, password) for s in password_selectors)

    if not (email_filled and pwd_filled):
        return False

    for s in submit_selectors:
        try:
            if page.locator(s).first.count() > 0:
                page.locator(s).first.click()
                break
        except Exception:
            continue

    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass

    return True


def is_session_state_valid(storage_path: str) -> bool:
    if not storage_path or not os.path.exists(storage_path):
        return False
    try:
        with open(storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cookies = data.get("cookies") or []
        return len(cookies) > 0
    except Exception:
        return False


def ensure_session(config: Optional[HeadoutConfig] = None) -> str:
    cfg = config or HeadoutConfig()
    storage_path = cfg.storage_state_path

    if is_session_state_valid(storage_path):
        return storage_path

    with sync_playwright() as p:
        browser_type = getattr(p, cfg.browser_engine)
        context: Optional[BrowserContext] = None

        if cfg.persistent:
            context = browser_type.launch_persistent_context(
                user_data_dir=cfg.user_data_dir,
                channel=cfg.browser_channel,
                headless=cfg.headless,
                viewport={"width": 1280, "height": 800},
            )
        else:
            browser = browser_type.launch(channel=cfg.browser_channel, headless=cfg.headless)
            context = browser.new_context()

        page = context.new_page()

        target_url = cfg.login_url or cfg.portal_url or "https://headout.com"
        try:
            page.goto(target_url, timeout=30000)
        except Exception:
            pass

        if cfg.email and cfg.password and cfg.login_url:
            attempt_credential_login(page, cfg.email, cfg.password)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

        time.sleep(2)

        context.storage_state(path=storage_path)
        context.close()

    return storage_path


if __name__ == "__main__":
    path = ensure_session()
    print(f"storage_state: {path}")

