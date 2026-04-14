"""Sales Navigator login, search, profile scraping, and InMail credits.

Selectors are centralized in the SELECTORS dict at the top of the file so
they're easy to update when LinkedIn ships UI changes. Every scrape field
is wrapped in a try/except that returns None on failure so a single broken
selector doesn't kill the whole scrape.
"""
import json
import re
import time
from typing import Iterator

from playwright.sync_api import Page, TimeoutError as PWTimeout

import config
import db
from automation import humanize
from logger import bus


SELECTORS = {
    # Login
    "login_email": "input#username",
    "login_password": "input#password",
    "login_submit": "button[type='submit']",
    # Sales Nav home markers
    "home_marker": "[data-view-name='search-filters']",
    # Search results
    "result_card": "[data-anonymize='person-name']",
    "result_link": "a[href*='/sales/lead/']",
    "result_container": "[data-x-search-result]",
    "next_page": "button[aria-label='Next']",
    # Profile page
    "profile_name": "[data-anonymize='person-name'], h1",
    "profile_title": "[data-anonymize='title'], [data-anonymize='job-title']",
    "profile_company": "[data-anonymize='company-name']",
    "profile_location": "[data-anonymize='location']",
    "profile_tenure": "[data-anonymize='tenure']",
    "shared_connections": "[data-sn-view-name='lead-shared-connections']",
    "teamlink": "[data-sn-view-name='lead-teamlink']",
    "viewed_your_profile": "text=/viewed your profile/i",
    "followed_company": "text=/follows your company/i",
    "recent_activity": "[data-sn-view-name='lead-activity']",
    # Account panel
    "account_size": "[data-anonymize='company-size']",
    "account_industry": "[data-anonymize='industry']",
    # InMail credits (shown in header on Sales Nav)
    "inmail_credits": "[data-control-name='inmail_credits'], text=/InMail credit/i",
    # 1st-degree indicator
    "first_degree_badge": "text=/1st/i",
    "already_invited": "text=/Pending|Invitation sent/i",
}


# ---------- login ----------


def ensure_logged_in(page: Page) -> None:
    """Navigate to Sales Nav; if login is required, drive the form and wait
    (up to 3 minutes) for the user to complete any 2FA manually.

    Detection is URL-based rather than DOM-selector-based because LinkedIn
    changes its DOM frequently but the URL structure is stable: any page
    under /sales/* that's not /sales/login* means we're authenticated.
    """
    bus.info("Opening Sales Navigator...")
    page.goto("https://www.linkedin.com/sales/home", wait_until="domcontentloaded")
    humanize.click_delay()
    bus.info(f"Landed at: {page.url}")

    def _is_sales_nav(url: str) -> bool:
        return "/sales/" in url and "login" not in url and "checkpoint" not in url

    if _is_sales_nav(page.url):
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PWTimeout:
            pass
        bus.success("Sales Navigator session active")
        return

    # On login page - try auto-fill, then wait for user to complete 2FA
    if "login" in page.url or "checkpoint" in page.url or "uas/login" in page.url:
        if config.LINKEDIN_EMAIL and config.LINKEDIN_PASSWORD:
            bus.info("Filling login form")
            try:
                page.fill(SELECTORS["login_email"], config.LINKEDIN_EMAIL)
                humanize.micro_delay()
                page.fill(SELECTORS["login_password"], config.LINKEDIN_PASSWORD)
                humanize.micro_delay()
                page.click(SELECTORS["login_submit"])
            except Exception as exc:
                bus.warn(f"Could not auto-fill login form: {exc}")

        bus.warn(
            "WAITING FOR 2FA - complete any security challenge in the Chromium "
            "window. Waiting up to 3 minutes for you to reach Sales Navigator."
        )
        deadline = time.time() + 180
        while time.time() < deadline:
            if _is_sales_nav(page.url):
                bus.success(f"Logged in to Sales Navigator (url={page.url})")
                return
            time.sleep(2)
        raise RuntimeError("Login timeout - 2FA or security challenge not completed")

    # Some other page (LinkedIn feed, error, interstitial) - try once more
    bus.warn(f"Unexpected landing page: {page.url} - navigating again")
    page.goto("https://www.linkedin.com/sales/home", wait_until="domcontentloaded")
    humanize.click_delay()
    bus.info(f"Retry landed at: {page.url}")
    if _is_sales_nav(page.url):
        try:
            page.wait_for_load_state("networkidle", timeout=10_000)
        except PWTimeout:
            pass
        bus.success("Sales Navigator session active")
        return
    raise RuntimeError(f"Could not reach Sales Navigator home (final url: {page.url})")


# ---------- InMail credits ----------


def get_inmail_credits(page: Page) -> int:
    """Best-effort read of the InMail credit balance from the header."""
    try:
        locator = page.locator(SELECTORS["inmail_credits"]).first
        text = locator.inner_text(timeout=3_000)
        match = re.search(r"(\d+)", text)
        if match:
            credits = int(match.group(1))
            db.set_setting("inmail_credits_remaining", str(credits))
            return credits
    except Exception:
        pass
    # Fall back to stored value
    try:
        return int(db.get_setting("inmail_credits_remaining", "0"))
    except ValueError:
        return 0


# ---------- search / list iteration ----------


def iter_leads_from_source(page: Page, source_url: str, max_leads: int) -> Iterator[str]:
    """Yield up to `max_leads` profile URLs from a Sales Nav search or saved list."""
    bus.info(f"Opening source: {source_url}")
    page.goto(source_url, wait_until="domcontentloaded")
    humanize.click_delay()
    humanize.random_scroll(page)

    yielded = 0
    max_pages = 5
    for _ in range(max_pages):
        if yielded >= max_leads:
            return
        # Wait for any result card
        try:
            page.wait_for_selector(SELECTORS["result_link"], timeout=10_000)
        except PWTimeout:
            bus.warn("No result links found on this page")
            return

        humanize.random_scroll(page)
        hrefs = page.eval_on_selector_all(
            SELECTORS["result_link"],
            "els => Array.from(new Set(els.map(e => e.href)))",
        )
        for href in hrefs:
            if yielded >= max_leads:
                return
            yield href
            yielded += 1

        # Pagination
        try:
            nxt = page.locator(SELECTORS["next_page"]).first
            if nxt.is_disabled():
                return
            nxt.click()
            humanize.click_delay()
        except Exception:
            return


# ---------- profile scrape ----------


def _safe_text(page: Page, selector: str) -> str | None:
    try:
        loc = page.locator(selector).first
        text = loc.inner_text(timeout=2_000).strip()
        return text or None
    except Exception:
        return None


def _exists(page: Page, selector: str) -> bool:
    try:
        return page.locator(selector).first.is_visible(timeout=1_500)
    except Exception:
        return False


def _detect_buying_signal(page: Page) -> str:
    if _exists(page, SELECTORS["viewed_your_profile"]):
        return "viewed_profile"
    if _exists(page, SELECTORS["followed_company"]):
        return "followed_company"
    if _exists(page, SELECTORS["teamlink"]):
        return "teamlink"
    return "none"


def _parse_tenure(text: str | None) -> tuple[float | None, float | None]:
    """Parse "2 yrs 3 mos in role" → (years_in_role, years_at_company)."""
    if not text:
        return None, None

    def _to_years(snippet: str) -> float | None:
        years = re.search(r"(\d+)\s*yr", snippet)
        months = re.search(r"(\d+)\s*mo", snippet)
        if not years and not months:
            return None
        y = int(years.group(1)) if years else 0
        m = int(months.group(1)) if months else 0
        return round(y + m / 12.0, 2)

    parts = re.split(r"[•|]", text)
    years_in_role = _to_years(parts[0]) if parts else None
    years_at_company = _to_years(parts[1]) if len(parts) > 1 else None
    return years_in_role, years_at_company


def scrape_profile(page: Page, profile_url: str) -> dict:
    """Visit a profile and pull every field we can find."""
    bus.info(f"Scraping {profile_url}")
    page.goto(profile_url, wait_until="domcontentloaded")
    humanize.click_delay()
    humanize.random_scroll(page)
    humanize.random_mouse_jitter(page)

    full_name = _safe_text(page, SELECTORS["profile_name"]) or "Unknown"
    parts = full_name.split(" ", 1)
    first_name = parts[0] if parts else None
    last_name = parts[1] if len(parts) > 1 else None

    tenure_text = _safe_text(page, SELECTORS["profile_tenure"])
    years_in_role, years_at_company = _parse_tenure(tenure_text)

    shared_connections: list[str] = []
    try:
        loc = page.locator(SELECTORS["shared_connections"]).first
        txt = loc.inner_text(timeout=2_000)
        shared_connections = [s.strip() for s in re.split(r",|\band\b", txt) if s.strip()]
    except Exception:
        pass

    teamlink = _safe_text(page, SELECTORS["teamlink"])

    recent_activity: list[str] = []
    try:
        loc = page.locator(SELECTORS["recent_activity"]).first
        txt = loc.inner_text(timeout=2_000)
        recent_activity = [s.strip() for s in txt.split("\n") if s.strip()][:5]
    except Exception:
        pass

    is_connected = 1 if _exists(page, SELECTORS["first_degree_badge"]) else 0

    lead = {
        "profile_url": profile_url,
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "title": _safe_text(page, SELECTORS["profile_title"]),
        "company": _safe_text(page, SELECTORS["profile_company"]),
        "location": _safe_text(page, SELECTORS["profile_location"]),
        "seniority": None,  # Sales Nav exposes this in filters; on profile it's implicit
        "department": None,
        "years_in_role": years_in_role,
        "years_at_company": years_at_company,
        "shared_connections_json": json.dumps(shared_connections) if shared_connections else None,
        "shared_experiences_json": None,
        "teamlink_connection": teamlink,
        "buying_signal": _detect_buying_signal(page),
        "recent_activity_json": json.dumps(recent_activity) if recent_activity else None,
        "account_company_size": _safe_text(page, SELECTORS["account_size"]),
        "account_industry": _safe_text(page, SELECTORS["account_industry"]),
        "account_technologies_json": None,
        "is_connected": is_connected,
    }
    return lead


def already_invited(page: Page) -> bool:
    """Returns True if we've already sent a connection request to this profile."""
    return _exists(page, SELECTORS["already_invited"])
