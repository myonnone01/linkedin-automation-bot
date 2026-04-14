"""Delivery methods: connect (with/without note), direct message, InMail.

All four methods share common behavior:
- Check for "already connected / already invited" state before acting.
- Respect LinkedIn-enforced character limits.
- Log every outcome via the caller; this module only raises on unexpected
  failures and returns status strings for expected outcomes.
"""
from playwright.sync_api import Page, TimeoutError as PWTimeout

import config
from automation import humanize, sales_nav
from logger import bus


# Buttons and modals share text across connect flows, so we use role/name
# locators where possible and fall back to text= selectors.


def _click_connect_button(page: Page) -> bool:
    """Find and click the primary Connect button on a Sales Nav profile.

    Sales Nav usually tucks Connect under a "More" dropdown. Try the dropdown
    first; if absent, try a top-level Connect button.
    """
    try:
        # Try the overflow button first
        more = page.get_by_role("button", name="More").first
        if more.is_visible(timeout=2_000):
            more.click()
            humanize.micro_delay()
    except Exception:
        pass

    for candidate in [
        page.get_by_role("menuitem", name="Connect").first,
        page.get_by_role("button", name="Connect").first,
        page.locator("button:has-text('Connect')").first,
    ]:
        try:
            if candidate.is_visible(timeout=2_000):
                candidate.click()
                return True
        except Exception:
            continue
    return False


def send_connect_no_note(page: Page, lead: dict) -> str:
    """Send a plain connection request with no note attached."""
    if sales_nav.already_invited(page):
        bus.info(f"Already invited: {lead.get('full_name')}")
        return "already_connected"

    if not _click_connect_button(page):
        bus.warn(f"Connect button not found for {lead.get('full_name')}")
        return "failed"
    humanize.click_delay()

    # Modal: "Send now" / "Send without a note"
    for candidate in [
        page.get_by_role("button", name="Send without a note").first,
        page.get_by_role("button", name="Send now").first,
        page.get_by_role("button", name="Send").first,
    ]:
        try:
            if candidate.is_visible(timeout=2_000):
                candidate.click()
                humanize.click_delay()
                bus.success(f"Connection request sent (no note): {lead.get('full_name')}")
                return "sent"
        except Exception:
            continue
    bus.warn(f"Could not confirm Send for {lead.get('full_name')}")
    return "failed"


def _fill_text_area(page, selector: str, text: str) -> bool:
    """Robustly fill a textarea or contenteditable.

    LinkedIn's new "Draft with AI" placeholder overlay can intercept
    clicks on the underlying textarea. We handle that by:
      1. Trying force=True click + human-like typing (best for stealth)
      2. Falling back to .fill() which bypasses overlays entirely
      3. Last resort: JavaScript value setter + input event
    Returns True if the text was successfully entered.
    """
    try:
        loc = page.locator(selector).first
        try:
            loc.click(force=True, timeout=5_000)
            humanize.type_like_human(loc, text)
            return True
        except Exception:
            pass
        # Fallback 1: fill() bypasses overlays
        try:
            loc.fill(text, timeout=5_000)
            return True
        except Exception:
            pass
        # Fallback 2: JS direct value set + dispatch input event
        try:
            loc.evaluate(
                "(el, val) => { el.value = val; "
                "el.dispatchEvent(new Event('input', {bubbles: true})); "
                "el.dispatchEvent(new Event('change', {bubbles: true})); }",
                text,
            )
            return True
        except Exception:
            return False
    except Exception:
        return False


def send_connection_note(page: Page, lead: dict, text: str) -> str:
    if not text:
        return "failed"
    if len(text) > config.CONNECTION_NOTE_LIMIT:
        text = text[: config.CONNECTION_NOTE_LIMIT]
    # Skip already-connected leads — connection_note doesn't apply
    if lead.get("is_connected"):
        bus.info(f"Already 1st-degree connected: {lead.get('full_name')}")
        return "already_connected"
    if sales_nav.already_invited(page):
        return "already_connected"

    if not _click_connect_button(page):
        return "failed"
    humanize.click_delay()

    # Click "Add a note" then type then Send
    try:
        add = page.get_by_role("button", name="Add a note").first
        if add.is_visible(timeout=2_000):
            add.click()
            humanize.micro_delay()
    except Exception:
        pass

    if not _fill_text_area(page, "textarea[name='message'], textarea", text):
        bus.warn(f"Could not type note for {lead.get('full_name')}")
        return "failed"

    humanize.click_delay()
    try:
        send = page.get_by_role("button", name="Send").first
        send.click()
        bus.success(f"Connection note sent: {lead.get('full_name')}")
        return "sent"
    except Exception as exc:
        bus.warn(f"Send button failed: {exc}")
        return "failed"


def send_linkedin_message(page: Page, lead: dict, text: str) -> str:
    if not text:
        return "failed"
    if not lead.get("is_connected"):
        return "skipped"

    try:
        msg_btn = page.get_by_role("button", name="Message").first
        msg_btn.click()
        humanize.click_delay()
    except Exception:
        bus.warn(f"Message button not found for {lead.get('full_name')}")
        return "failed"

    if not _fill_text_area(page, "div[contenteditable='true']", text):
        bus.warn(f"Could not type message for {lead.get('full_name')}")
        return "failed"

    humanize.click_delay()
    try:
        send = page.get_by_role("button", name="Send").first
        send.click()
        bus.success(f"Direct message sent: {lead.get('full_name')}")
        return "sent"
    except Exception as exc:
        bus.warn(f"Send failed: {exc}")
        return "failed"


def send_inmail(page: Page, lead: dict, text: str) -> str:
    if not text:
        return "failed"
    if len(text) > config.INMAIL_LIMIT:
        text = text[: config.INMAIL_LIMIT]

    credits = sales_nav.get_inmail_credits(page)
    if credits <= 0:
        bus.warn(f"InMail credits exhausted (remaining={credits})")
        return "credits_exhausted"

    try:
        inmail_btn = page.get_by_role("button", name="InMail").first
        if not inmail_btn.is_visible(timeout=2_000):
            return "inmail_unavailable"
        inmail_btn.click()
        humanize.click_delay()
    except Exception:
        return "inmail_unavailable"

    # Subject (optional) + body
    try:
        subject = page.locator("input[name='subject'], input[aria-label='Subject']").first
        if subject.is_visible(timeout=1_500):
            humanize.type_like_human(subject, "Quick hello")
    except Exception:
        pass

    if not _fill_text_area(page, "textarea, div[contenteditable='true']", text):
        bus.warn(f"Could not type InMail body for {lead.get('full_name')}")
        return "failed"

    humanize.click_delay()
    try:
        send = page.get_by_role("button", name="Send").first
        send.click()
        bus.success(f"InMail sent: {lead.get('full_name')}")
        return "sent"
    except Exception as exc:
        bus.warn(f"InMail send failed: {exc}")
        return "failed"


def detect_reply(page: Page, lead: dict) -> bool:
    """Best-effort: open the 1:1 thread and check whose message is last.

    Returns True if the most recent message is from the lead (not from us).
    Silently returns False if we can't find a thread.
    """
    try:
        msg_btn = page.get_by_role("button", name="Message").first
        if not msg_btn.is_visible(timeout=2_000):
            return False
        msg_btn.click()
        humanize.click_delay()
    except Exception:
        return False

    try:
        # The last message bubble in the open thread
        bubbles = page.locator("[data-sn-view-name='messaging-message']")
        count = bubbles.count()
        if count == 0:
            return False
        last = bubbles.nth(count - 1)
        text = last.inner_text(timeout=2_000)
        # If the last bubble is not attributed to "You" / "Mike", treat as reply
        return "You" not in text.split("\n")[0]
    except Exception:
        return False
