"""Playwright persistent-context launcher.

We use `launch_persistent_context` so LinkedIn session cookies and any 2FA
challenge responses survive between runs. On first run you log in manually
in the visible Chromium window; subsequent runs reuse that profile.
"""
from contextlib import contextmanager

from playwright.sync_api import sync_playwright, BrowserContext, Page

import config
from logger import bus


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36"
)


@contextmanager
def launch():
    """Yield (context, page). Cleans up on exit."""
    config.PW_PROFILE_DIR.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        bus.info("Launching Chromium (persistent profile)")
        context: BrowserContext = pw.chromium.launch_persistent_context(
            user_data_dir=str(config.PW_PROFILE_DIR),
            headless=False,
            viewport={"width": 1366, "height": 820},
            user_agent=USER_AGENT,
            locale="en-US",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-default-browser-check",
                "--no-first-run",
            ],
        )
        if context.pages:
            page: Page = context.pages[0]
        else:
            page = context.new_page()
        try:
            yield context, page
        finally:
            try:
                context.close()
            except Exception:
                pass
            bus.info("Chromium closed")
