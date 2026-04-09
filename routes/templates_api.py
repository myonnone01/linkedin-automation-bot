"""CRUD for prompt templates."""
from flask import Blueprint, jsonify, request

import config
import db

bp = Blueprint("templates_api", __name__, url_prefix="/api/templates")


def _validate(data: dict) -> str | None:
    if not data.get("name"):
        return "name is required"
    if data.get("delivery_method") not in config.DELIVERY_METHODS:
        return f"delivery_method must be one of {config.DELIVERY_METHODS}"
    if data["delivery_method"] != config.DELIVERY_CONNECT_NO_NOTE:
        if not data.get("message_angle"):
            return "message_angle is required for this delivery method"
    return None


@bp.route("", methods=["GET"])
def list_all():
    return jsonify(db.list_templates())


@bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True)
    err = _validate(data)
    if err:
        return jsonify({"error": err}), 400
    template_id = db.create_template(data)
    return jsonify({"id": template_id}), 201


@bp.route("/<int:template_id>", methods=["PUT"])
def update(template_id: int):
    data = request.get_json(force=True)
    err = _validate(data)
    if err:
        return jsonify({"error": err}), 400
    if not db.get_template(template_id):
        return jsonify({"error": "not found"}), 404
    db.update_template(template_id, data)
    return jsonify({"ok": True})


@bp.route("/<int:template_id>", methods=["DELETE"])
def delete(template_id: int):
    db.delete_template(template_id)
    return jsonify({"ok": True})
