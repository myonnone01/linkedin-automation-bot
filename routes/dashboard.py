"""Dashboard page, stats endpoint, SSE log stream."""
from flask import Blueprint, Response, jsonify, render_template, stream_with_context

import db
from logger import bus, sse_stream
from sequences import engine

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    return render_template(
        "dashboard.html",
        sequences=db.list_sequences(),
        daily_limit=int(db.get_setting("daily_limit", "20")),
    )


@bp.route("/templates-page")
def templates_page():
    return render_template(
        "templates.html",
        templates=db.list_templates(),
        sequences=db.list_sequences(),
    )


@bp.route("/sequences-page")
def sequences_page():
    sequences = db.list_sequences()
    sequences_with_steps = []
    for seq in sequences:
        seq["steps"] = db.list_steps(seq["id"])
        sequences_with_steps.append(seq)
    return render_template(
        "sequences.html",
        sequences=sequences_with_steps,
        templates=db.list_templates(),
    )


@bp.route("/pipeline-page")
def pipeline_page():
    return render_template(
        "pipeline.html",
        counts=db.pipeline_counts(),
        sequences=db.list_sequences(),
    )


@bp.route("/logs-page")
def logs_page():
    return render_template(
        "logs.html",
        messages=db.list_messages(limit=500),
    )


@bp.route("/api/stats")
def api_stats():
    today = db.stats_today()
    alltime = db.stats_alltime()
    pipeline = db.pipeline_counts()
    return jsonify(
        {
            "today": today,
            "alltime": alltime,
            "pipeline": pipeline,
            "inmail_credits": int(db.get_setting("inmail_credits_remaining", "0")),
            "session_running": engine.is_running(),
        }
    )


@bp.route("/logs/stream")
def logs_stream():
    q = bus.subscribe()

    @stream_with_context
    def gen():
        yield from sse_stream(q)

    return Response(gen(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })
