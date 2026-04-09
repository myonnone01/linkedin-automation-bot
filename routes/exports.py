"""CSV export of the message log."""
import csv
import io

from flask import Blueprint, Response

import db

bp = Blueprint("exports", __name__, url_prefix="/api/export")


CSV_COLUMNS = [
    "profile_url",
    "name",
    "title",
    "company",
    "seniority",
    "buying_signal",
    "sequence",
    "step",
    "delivery_method",
    "ai_message_sent",
    "status",
    "timestamp",
]


@bp.route("/csv")
def export_csv():
    messages = db.list_messages(limit=10_000)
    sequences = {s["id"]: s["name"] for s in db.list_sequences()}

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()

    for msg in messages:
        lead = None
        if msg.get("lead_id"):
            lead = db.get_lead(msg["lead_id"]) or {}
        else:
            lead = {}
        writer.writerow({
            "profile_url": lead.get("profile_url") or msg.get("profile_url") or "",
            "name": lead.get("full_name") or msg.get("full_name") or "",
            "title": lead.get("title") or msg.get("title") or "",
            "company": lead.get("company") or msg.get("company") or "",
            "seniority": lead.get("seniority") or "",
            "buying_signal": lead.get("buying_signal") or "",
            "sequence": sequences.get(msg.get("sequence_id"), ""),
            "step": msg.get("step_number") or "",
            "delivery_method": msg.get("delivery_method") or "",
            "ai_message_sent": msg.get("ai_message") or "",
            "status": msg.get("status") or "",
            "timestamp": msg.get("timestamp") or "",
        })

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=linkedin_automation_log.csv"
        },
    )
