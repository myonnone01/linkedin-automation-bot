"""Seed the database with starter templates and sequences.

Run manually with `python seed.py` to populate the database with a few
working examples so your first session can start without building
templates/sequences from scratch in the UI. Safe to re-run: it skips any
template or sequence whose name already exists.

You can always edit or delete these from the Templates / Sequences pages.
"""
import sys

import db


STARTER_TEMPLATES = [
    {
        "name": "Warm connect (no note)",
        "delivery_method": "connect_no_note",
        "target_role_keywords": "",
        "target_seniority": "",
        "message_angle": "",
    },
    {
        "name": "IT Director intro note",
        "delivery_method": "connection_note",
        "target_role_keywords": "director,head of it,it director",
        "target_seniority": "director",
        "message_angle": (
            "Reference the TeamLink shared connection if present, otherwise "
            "lead with relevance to their role at {{company}}. Mention that "
            "Presidio has helped similar {{company}}-sized IT orgs modernize "
            "their infrastructure and security stack. Keep it under 300 "
            "characters to leave room for warmth. Do NOT pitch in the note "
            "itself — just open the door."
        ),
    },
    {
        "name": "IT Director follow-up message",
        "delivery_method": "linkedin_message",
        "target_role_keywords": "director,head of it",
        "target_seniority": "director",
        "message_angle": (
            "This is the day-3 follow-up after connecting. Thank {{first_name}} "
            "briefly for connecting, then share one concrete Presidio capability "
            "relevant to their stack (e.g. Zero Trust rollout, SOC-as-a-Service, "
            "hybrid cloud migration). Ask if a 15-minute intro call next week "
            "would be useful. Two short paragraphs, no more than 4 sentences total."
        ),
    },
    {
        "name": "VP Engineering value-prop",
        "delivery_method": "connection_note",
        "target_role_keywords": "vp engineering,vice president engineering,head of engineering",
        "target_seniority": "vp",
        "message_angle": (
            "Open with any buying signal ({{buying_signal}}) if present. "
            "For VP Engineering contacts, focus on platform reliability, "
            "developer productivity, and cloud cost optimization — NOT "
            "cybersecurity or managed services pitches. Mention Presidio's "
            "cloud engineering practice. Under 300 characters."
        ),
    },
    {
        "name": "C-Level executive InMail",
        "delivery_method": "inmail",
        "target_role_keywords": "cio,cto,ciso,chief",
        "target_seniority": "c_level",
        "message_angle": (
            "This is a Sales Navigator InMail to a C-level executive. "
            "Subject should be quiet and relevant, not salesy. Open by "
            "acknowledging the weight of their role. Reference one current, "
            "plausible strategic priority in the {{company}} industry. "
            "Mention Presidio's work with a peer company (no names). "
            "Close with a low-pressure ask — a 15-minute point-of-view call. "
            "Keep to 4-6 sentences. Sign off as Mike."
        ),
    },
]


STARTER_SEQUENCES = [
    {
        "sequence": {
            "name": "IT Director 4-step",
            "segment_role_keywords": "director,head of it,it director",
            "segment_seniority": "director",
        },
        "steps": [
            {"step_number": 1, "delay_days": 0,
             "delivery_method": "connection_note",
             "template_name": "IT Director intro note"},
            {"step_number": 2, "delay_days": 3,
             "delivery_method": "linkedin_message",
             "template_name": "IT Director follow-up message"},
            {"step_number": 3, "delay_days": 7,
             "delivery_method": "linkedin_message",
             "template_name": "IT Director follow-up message"},
            {"step_number": 4, "delay_days": 14,
             "delivery_method": "linkedin_message",
             "template_name": "IT Director follow-up message"},
        ],
    },
    {
        "sequence": {
            "name": "VP Engineering 3-step",
            "segment_role_keywords": "vp engineering,vice president engineering",
            "segment_seniority": "vp",
        },
        "steps": [
            {"step_number": 1, "delay_days": 0,
             "delivery_method": "connection_note",
             "template_name": "VP Engineering value-prop"},
            {"step_number": 2, "delay_days": 5,
             "delivery_method": "linkedin_message",
             "template_name": "VP Engineering value-prop"},
            {"step_number": 3, "delay_days": 12,
             "delivery_method": "linkedin_message",
             "template_name": "VP Engineering value-prop"},
        ],
    },
    {
        "sequence": {
            "name": "Network growth (connect only)",
            "segment_role_keywords": "",
            "segment_seniority": "",
        },
        "steps": [
            {"step_number": 1, "delay_days": 0,
             "delivery_method": "connect_no_note",
             "template_name": None},
        ],
    },
]


def _template_id_by_name(name: str) -> int | None:
    for t in db.list_templates():
        if t["name"] == name:
            return t["id"]
    return None


def _sequence_id_by_name(name: str) -> int | None:
    for s in db.list_sequences():
        if s["name"] == name:
            return s["id"]
    return None


def seed() -> None:
    db.init_db()
    print("Seeding database with starter templates and sequences…")

    existing_templates = {t["name"] for t in db.list_templates()}
    for tpl in STARTER_TEMPLATES:
        if tpl["name"] in existing_templates:
            print(f"  - template '{tpl['name']}' already exists, skipping")
            continue
        db.create_template(tpl)
        print(f"  + template '{tpl['name']}'")

    existing_sequences = {s["name"] for s in db.list_sequences()}
    for entry in STARTER_SEQUENCES:
        seq = entry["sequence"]
        if seq["name"] in existing_sequences:
            print(f"  - sequence '{seq['name']}' already exists, skipping steps")
            continue
        sequence_id = db.create_sequence(seq)
        print(f"  + sequence '{seq['name']}' (id={sequence_id})")
        for step in entry["steps"]:
            template_id = None
            if step.get("template_name"):
                template_id = _template_id_by_name(step["template_name"])
                if template_id is None:
                    print(f"      ! template '{step['template_name']}' missing, "
                          f"step {step['step_number']} will have no template")
            db.create_step(sequence_id, {
                "step_number": step["step_number"],
                "delay_days": step["delay_days"],
                "delivery_method": step["delivery_method"],
                "template_id": template_id,
            })
            print(f"      + step {step['step_number']} "
                  f"({step['delivery_method']}, +{step['delay_days']}d)")

    print("Done. Open http://localhost:5000 to review and edit.")


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
