"""Anthropic Claude wrapper for outreach message generation."""
import json
import re
from typing import Any

from anthropic import Anthropic

import config
from logger import bus


_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env and restart."
            )
        _client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def _substitute_hints(angle: str, lead: dict) -> str:
    """Fill {{first_name}} / {{company}} / etc. into the angle template."""
    mapping = {
        "first_name": lead.get("first_name") or "",
        "last_name": lead.get("last_name") or "",
        "company": lead.get("company") or "",
        "title": lead.get("title") or "",
        "shared_connection": lead.get("teamlink_connection") or "",
        "buying_signal": lead.get("buying_signal") or "",
        "pain_point": "",  # caller may override
    }
    out = angle
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out


def _lead_snapshot(lead: dict) -> dict:
    """Trimmed JSON representation of a lead, for the user prompt."""
    keys = [
        "full_name", "first_name", "title", "company", "location",
        "seniority", "department", "years_in_role", "years_at_company",
        "teamlink_connection", "buying_signal",
        "account_company_size", "account_industry",
    ]
    snap: dict[str, Any] = {k: lead.get(k) for k in keys if lead.get(k) is not None}
    for json_field in ("shared_connections_json", "shared_experiences_json",
                       "recent_activity_json", "account_technologies_json"):
        raw = lead.get(json_field)
        if raw:
            try:
                snap[json_field.replace("_json", "")] = json.loads(raw)
            except (TypeError, ValueError):
                pass
    return snap


def _postprocess(text: str, limit: int) -> tuple[str, bool]:
    """Strip quotes/whitespace; hard-truncate to limit. Returns (text, truncated)."""
    text = text.strip()
    # Strip outer smart or straight quotes if Claude wrapped the message
    if len(text) >= 2 and text[0] in ('"', "'", "\u201c") and text[-1] in ('"', "'", "\u201d"):
        text = text[1:-1].strip()
    # Collapse runs of whitespace but preserve paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    truncated = False
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "..."
        truncated = True
    return text, truncated


def generate_message(lead: dict, template: dict, delivery_method: str) -> str:
    """Ask Claude to write a personalized message for this lead + template.

    Returns the final, char-limited message body. Never returns an empty string
    for methods that require a message - raises on API failure so the caller
    can log `failed` and skip the send.
    """
    limit = config.DELIVERY_CHAR_LIMITS.get(delivery_method, 500)
    angle = _substitute_hints(template.get("message_angle", ""), lead)
    snapshot = _lead_snapshot(lead)

    buying_signal = lead.get("buying_signal")
    signal_instruction = ""
    if buying_signal and buying_signal != "none":
        signal_instruction = (
            f"\n\nIMPORTANT: This lead has a buying signal: '{buying_signal}'. "
            "Open the message by referencing this signal naturally - do not "
            "mention the word 'signal' itself."
        )

    delivery_guidance = {
        config.DELIVERY_CONNECTION_NOTE: (
            "This is a LinkedIn connection request note. Keep it under "
            f"{limit} characters. Be warm and brief - one or two sentences."
        ),
        config.DELIVERY_LINKEDIN_MESSAGE: (
            "This is a LinkedIn direct message to a 1st-degree connection. "
            "Two to four short sentences is ideal."
        ),
        config.DELIVERY_INMAIL: (
            "This is a Sales Navigator InMail. Slightly longer (3-5 sentences) "
            f"is fine. Under {limit} characters."
        ),
    }.get(delivery_method, "")

    user_prompt = (
        f"Lead profile (JSON):\n```json\n{json.dumps(snapshot, indent=2)}\n```\n\n"
        f"Message angle / goal:\n{angle}\n\n"
        f"Delivery channel guidance:\n{delivery_guidance}"
        f"{signal_instruction}\n\n"
        "Write ONLY the message body, no preamble, no subject line, no quotes, "
        "no sign-off beyond 'Mike' if appropriate. Do not use em-dashes. Do not "
        "start with 'Hi' followed by something generic - lead with relevance."
    )

    client = _get_client()
    bus.info(f"Calling Claude ({config.ANTHROPIC_MODEL}) for {lead.get('full_name', 'lead')}")
    try:
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=config.CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:
        bus.error(f"Claude API error: {exc}")
        raise

    # Collect text from content blocks
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    raw = "".join(parts)
    final, truncated = _postprocess(raw, limit)
    if truncated:
        bus.warn(f"Message truncated to {limit} chars for {lead.get('full_name', 'lead')}")
    return final
