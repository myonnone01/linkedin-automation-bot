"""CRUD for sequences and their steps."""
from flask import Blueprint, jsonify, request

import config
import db

bp = Blueprint("sequences_api", __name__, url_prefix="/api/sequences")


@bp.route("", methods=["GET"])
def list_all():
    sequences = db.list_sequences()
    for seq in sequences:
        seq["steps"] = db.list_steps(seq["id"])
    return jsonify(sequences)


@bp.route("", methods=["POST"])
def create():
    data = request.get_json(force=True)
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    sequence_id = db.create_sequence(data)
    return jsonify({"id": sequence_id}), 201


@bp.route("/<int:sequence_id>", methods=["PUT"])
def update(sequence_id: int):
    data = request.get_json(force=True)
    if not db.get_sequence(sequence_id):
        return jsonify({"error": "not found"}), 404
    db.update_sequence(sequence_id, data)
    return jsonify({"ok": True})


@bp.route("/<int:sequence_id>", methods=["DELETE"])
def delete(sequence_id: int):
    db.delete_sequence(sequence_id)
    return jsonify({"ok": True})


@bp.route("/<int:sequence_id>/steps", methods=["POST"])
def add_step(sequence_id: int):
    data = request.get_json(force=True)
    if data.get("delivery_method") not in config.DELIVERY_METHODS:
        return jsonify({"error": "invalid delivery_method"}), 400
    if "step_number" not in data or "delay_days" not in data:
        return jsonify({"error": "step_number and delay_days are required"}), 400
    step_id = db.create_step(sequence_id, data)
    return jsonify({"id": step_id}), 201


@bp.route("/<int:sequence_id>/steps/<int:step_id>", methods=["DELETE"])
def delete_step(sequence_id: int, step_id: int):
    db.delete_step(step_id)
    return jsonify({"ok": True})
