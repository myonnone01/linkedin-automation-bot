"""Session start/stop endpoints."""
import threading

from flask import Blueprint, jsonify, request

import config
import db
from logger import bus
from sequences import engine

bp = Blueprint("runs", __name__, url_prefix="/api/runs")


@bp.route("/start", methods=["POST"])
def start():
    if engine.is_running():
        return jsonify({"error": "A session is already running"}), 409

    data = request.get_json(force=True) or {}
    source_url = (data.get("source_url") or "").strip() or None
    sequence_id = data.get("sequence_id")
    daily_limit = int(data.get("daily_limit") or config.DAILY_LIMIT)
    connect_only = bool(data.get("connect_only"))

    if connect_only and not source_url:
        return jsonify({"error": "source_url is required for connect-only mode"}), 400
    if source_url and not connect_only and not sequence_id:
        return jsonify({"error": "sequence_id is required when seeding from a source"}), 400

    # Persist daily limit for reuse
    db.set_setting("daily_limit", str(daily_limit))

    thread = threading.Thread(
        target=engine.run_session,
        kwargs={
            "source_url": source_url,
            "sequence_id": int(sequence_id) if sequence_id else None,
            "daily_limit": daily_limit,
            "connect_only": connect_only,
        },
        daemon=True,
    )
    thread.start()
    bus.info("Session thread launched")
    return jsonify({"ok": True})


@bp.route("/stop", methods=["POST"])
def stop():
    if not engine.is_running():
        return jsonify({"error": "No session is running"}), 409
    engine.request_cancel()
    return jsonify({"ok": True})


@bp.route("/status", methods=["GET"])
def status():
    return jsonify({"running": engine.is_running()})
