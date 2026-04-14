"""Sequence engine: seeding from a source URL and sweeping due contacts.

The engine is invoked only when the user clicks **Start** in the UI. It runs
inside a worker thread (guarded by a lock so only one session runs at a time)
and periodically checks a cancel flag so Stop is cooperative.
"""
import threading
from datetime import datetime, timedelta
from typing import Callable

import config
import db
from ai import claude_client
from automation import browser, humanize, messaging, sales_nav
from logger import bus


# Session control - one session at a time.
_session_lock = threading.Lock()
_cancel_flag = threading.Event()
_session_running = threading.Event()


def is_running() -> bool:
    return _session_running.is_set()


def request_cancel() -> None:
    _cancel_flag.set()
    bus.warn("Cancel requested - session will stop after current action")


def _check_cancelled() -> bool:
    return _cancel_flag.is_set()


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _send_for_step(page, lead: dict, step: dict, template: dict | None) -> tuple[str, str]:
    """Dispatch to the correct messenger. Returns (status, ai_message)."""
    method = step["delivery_method"]

    if method == config.DELIVERY_CONNECT_NO_NOTE:
        return messaging.send_connect_no_note(page, lead), ""

    if not template:
        bus.warn(f"No template assigned for step {step['step_number']}")
        return "failed", ""

    try:
        ai_message = claude_client.generate_message(lead, template, method)
    except Exception as exc:
        bus.error(f"Claude call failed: {exc}")
        return "failed", ""

    if method == config.DELIVERY_CONNECTION_NOTE:
        return messaging.send_connection_note(page, lead, ai_message), ai_message
    if method == config.DELIVERY_LINKEDIN_MESSAGE:
        return messaging.send_linkedin_message(page, lead, ai_message), ai_message
    if method == config.DELIVERY_INMAIL:
        return messaging.send_inmail(page, lead, ai_message), ai_message

    bus.warn(f"Unknown delivery method: {method}")
    return "failed", ai_message


def _match_template_for_step(step: dict) -> dict | None:
    if step.get("template_id"):
        return db.get_template(step["template_id"])
    return None


def _seed_from_source(page, source_url: str, sequence_id: int, max_leads: int) -> int:
    """Scrape the source and create contact_state rows at step 0."""
    bus.info(f"Seeding leads from source (sequence_id={sequence_id})")
    count = 0
    for profile_url in sales_nav.iter_leads_from_source(page, source_url, max_leads):
        if _check_cancelled():
            break
        try:
            lead = sales_nav.scrape_profile(page, profile_url)
            lead_id = db.upsert_lead(lead)
            db.upsert_contact_state(lead_id, sequence_id, _now_iso())
            count += 1
            bus.info(f"Seeded {lead['full_name']} ({count}/{max_leads})")
            humanize.profile_delay()
        except Exception as exc:
            bus.error(f"Scrape failed for {profile_url}: {exc}")
    bus.success(f"Seeded {count} leads into sequence {sequence_id}")
    return count


def _process_due(page, daily_cap: int) -> int:
    """Run one sweep through contact_state. Returns the number of actions taken."""
    now = _now_iso()
    due = db.list_due_contacts(now)
    if not due:
        bus.info("No contacts due")
        return 0

    bus.info(f"{len(due)} contacts due - processing up to {daily_cap}")
    actions = 0
    for row in due:
        if _check_cancelled() or actions >= daily_cap:
            break

        sequence_id = row["sequence_id"]
        current_step = row["current_step"] or 0
        next_step_number = current_step + 1
        step = db.get_step(sequence_id, next_step_number)
        if not step:
            # No more steps - mark completed
            db.advance_contact(row["id"], current_step, None, completed=True)
            db.log_message(
                lead_id=row["lead_id"],
                sequence_id=sequence_id,
                step_number=current_step,
                delivery_method="",
                ai_message="",
                status="sequence_complete",
            )
            bus.info(f"Sequence complete for {row['full_name']}")
            continue

        lead = db.get_lead(row["lead_id"])
        if not lead:
            continue

        # Navigate to profile & rescrape connection status
        try:
            fresh = sales_nav.scrape_profile(page, lead["profile_url"])
            lead.update(fresh)
            db.upsert_lead(lead)
        except Exception as exc:
            bus.error(f"Scrape failed for {lead['profile_url']}: {exc}")
            db.log_message(
                lead_id=lead["id"],
                sequence_id=sequence_id,
                step_number=next_step_number,
                delivery_method=step["delivery_method"],
                ai_message="",
                status="failed",
                error=str(exc),
            )
            continue

        # Reply detection
        if messaging.detect_reply(page, lead):
            db.mark_replied(row["id"])
            db.log_message(
                lead_id=lead["id"],
                sequence_id=sequence_id,
                step_number=next_step_number,
                delivery_method=step["delivery_method"],
                ai_message="",
                status="replied",
            )
            bus.success(f"Reply detected from {lead['full_name']} - marking sequence replied")
            continue

        template = _match_template_for_step(step)
        status, ai_message = _send_for_step(page, lead, step, template)

        db.log_message(
            lead_id=lead["id"],
            sequence_id=sequence_id,
            step_number=next_step_number,
            delivery_method=step["delivery_method"],
            ai_message=ai_message,
            status=status,
        )
        actions += 1

        if status == "sent":
            # Advance to next step
            next_next_step = db.get_step(sequence_id, next_step_number + 1)
            if next_next_step:
                next_dt = datetime.utcnow() + timedelta(days=next_next_step["delay_days"])
                db.advance_contact(
                    row["id"], next_step_number, next_dt.isoformat(timespec="seconds")
                )
            else:
                db.advance_contact(row["id"], next_step_number, None, completed=True)

        humanize.profile_delay()

    return actions


def _connect_only_sweep(page, source_url: str, daily_cap: int) -> int:
    """One-off mode: scrape source URL and connect to every lead with no note,
    bypassing sequences entirely. Used by the dashboard "Connect only" toggle."""
    bus.info("Running CONNECT-ONLY sweep (no sequences, no Claude)")
    actions = 0
    for profile_url in sales_nav.iter_leads_from_source(page, source_url, daily_cap):
        if _check_cancelled() or actions >= daily_cap:
            break
        try:
            lead = sales_nav.scrape_profile(page, profile_url)
            lead_id = db.upsert_lead(lead)
            lead["id"] = lead_id
        except Exception as exc:
            bus.error(f"Scrape failed for {profile_url}: {exc}")
            continue

        if lead.get("is_connected"):
            db.log_message(
                lead_id=lead_id, sequence_id=None, step_number=None,
                delivery_method=config.DELIVERY_CONNECT_NO_NOTE,
                ai_message="", status="already_connected",
            )
            humanize.profile_delay()
            continue

        status = messaging.send_connect_no_note(page, lead)
        db.log_message(
            lead_id=lead_id, sequence_id=None, step_number=None,
            delivery_method=config.DELIVERY_CONNECT_NO_NOTE,
            ai_message="", status=status,
        )
        if status == "sent":
            actions += 1
        humanize.profile_delay()
    return actions


def run_session(
    *,
    source_url: str | None,
    sequence_id: int | None,
    daily_limit: int,
    connect_only: bool,
) -> None:
    """Top-level entry point for a worker thread."""
    if not _session_lock.acquire(blocking=False):
        bus.warn("Another session is already running - refusing to start")
        return

    _cancel_flag.clear()
    _session_running.set()
    db.set_setting("session_running", "1")
    bus.info("===== SESSION START =====")

    try:
        daily_cap = min(daily_limit, config.SESSION_MAX_ACTIONS)
        with browser.launch() as (context, page):
            sales_nav.ensure_logged_in(page)
            sales_nav.get_inmail_credits(page)

            total = 0
            if connect_only and source_url:
                total += _connect_only_sweep(page, source_url, daily_cap)
            else:
                if source_url and sequence_id:
                    _seed_from_source(page, source_url, sequence_id, daily_cap)
                remaining = max(0, daily_cap - total)
                if remaining:
                    total += _process_due(page, remaining)

            bus.success(f"===== SESSION END ({total} actions) =====")
    except Exception as exc:
        bus.error(f"Session aborted: {exc}")
    finally:
        db.set_setting("session_running", "0")
        _session_running.clear()
        _cancel_flag.clear()
        _session_lock.release()
