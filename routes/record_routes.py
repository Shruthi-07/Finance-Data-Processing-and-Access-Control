"""
record_routes.py
POST   /api/records/          → Admin: create
GET    /api/records/          → Role-based list (paginated, filterable)
GET    /api/records/export    → CSV export
GET    /api/records/<id>      → Single record
PUT    /api/records/<id>      → Admin: update
DELETE /api/records/<id>      → Admin: soft-delete

Query params for GET /:
    type, category, date_from (YYYY-MM-DD), date_to (YYYY-MM-DD),
    search, page (default 1), limit (default 20, max 100)
"""

import csv
import io
from flask import Blueprint, request, jsonify, g, Response
from extensions import mysql
from db import get_connection
from utils.decorators    import token_required, roles_required
from utils.validators    import validate_record
from utils.audit         import log_action
from models.record_model import (
    create_record, get_all_records, get_records_by_user,
    get_record_by_id, update_record, soft_delete_record,
    count_all_records, count_records_by_user,
    get_all_records_for_export
)

record_bp = Blueprint("records", __name__)


def _parse_filters():
    return {
        "rec_type":  request.args.get("type"),
        "category":  request.args.get("category"),
        "date_from": request.args.get("date_from"),
        "date_to":   request.args.get("date_to"),
        "search":    request.args.get("search"),
    }


def _serialize(records):
    for r in records:
        if r.get("date"):       r["date"]       = str(r["date"])
        if r.get("created_at"): r["created_at"] = str(r["created_at"])
    return records


# ── Create ────────────────────────────────────────────────────
@record_bp.route("/", methods=["POST"])
@token_required
@roles_required("admin")
def add_record():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    is_valid, error = validate_record(data)
    if not is_valid:
        return jsonify({"error": error}), 422

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 422
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        conn.close()
        return jsonify({"error": f"Invalid user_id: {user_id}"}), 400
    
    new_id = create_record(
        cur,
        user_id     = user_id,
        amount      = data["amount"],
        rec_type    = data["type"],
        category    = data["category"],
        date        = data["date"],
        description = data.get("description", "")
    )
    log_action(cur, g.user["user_id"], "record_created",
               f"Record #{new_id} created for user {user_id}")
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Record created successfully", "id": new_id}), 201


# ── List (paginated) ──────────────────────────────────────────
@record_bp.route("/", methods=["GET"])
@token_required
def list_records():
    role    = g.user["role"]
    user_id = g.user["user_id"]
    filters = _parse_filters()

    try:
        page  = max(1, int(request.args.get("page", 1)))
        limit = min(100, max(1, int(request.args.get("limit", 20))))
    except ValueError:
        page, limit = 1, 20
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    if role in ("admin", "analyst"):
        records = get_all_records(cur, **filters, page=page, limit=limit)
        total   = count_all_records(cur, **filters)
    else:
        records = get_records_by_user(cur, user_id, **filters, page=page, limit=limit)
        total   = count_records_by_user(cur, user_id, **filters)

    cur.close()
    conn.close()
    return jsonify({
        "records":    _serialize(records),
        "count":      len(records),
        "total":      total,
        "page":       page,
        "limit":      limit,
        "total_pages": max(1, -(-total // limit))   # ceiling division
    }), 200


# ── CSV Export ────────────────────────────────────────────────
@record_bp.route("/export", methods=["GET"])
@token_required
def export_records():
    role    = g.user["role"]
    user_id = g.user["user_id"]
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    records = get_all_records_for_export(
        cur, user_id=(None if role in ("admin", "analyst") else user_id)
    )
    log_action(cur, user_id, "records_exported", f"role={role}")
    conn.commit()
    cur.close()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "amount", "type", "category", "date", "description", "created_at"])
    for r in records:
        writer.writerow([
            r["id"], r["user_id"], r["amount"], r["type"],
            r["category"], r["date"], r.get("description", ""), r["created_at"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=records_export.csv"}
    )


# ── Single Record ─────────────────────────────────────────────
@record_bp.route("/<int:record_id>", methods=["GET"])
@token_required
def get_record(record_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    record = get_record_by_id(cur, record_id)
    cur.close()
    conn.close()
    if not record:
        return jsonify({"error": "Record not found"}), 404

    if g.user["role"] == "viewer" and record["user_id"] != g.user["user_id"]:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"record": _serialize([record])[0]}), 200


# ── Update ────────────────────────────────────────────────────
@record_bp.route("/<int:record_id>", methods=["PUT"])
@token_required
@roles_required("admin")
def edit_record(record_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    is_valid, error = validate_record(data)
    if not is_valid:
        return jsonify({"error": error}), 422
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    record = get_record_by_id(cur, record_id)
    if not record:
        cur.close()
        return jsonify({"error": "Record not found"}), 404

    update_record(
        cur,
        record_id   = record_id,
        amount      = data["amount"],
        rec_type    = data["type"],
        category    = data["category"],
        date        = data["date"],
        description = data.get("description", "")
    )
    log_action(cur, g.user["user_id"], "record_updated", f"Record #{record_id} updated")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": f"Record {record_id} updated successfully"}), 200


# ── Soft Delete ───────────────────────────────────────────────
@record_bp.route("/<int:record_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def remove_record(record_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    record = get_record_by_id(cur, record_id)
    if not record:
        cur.close()
        return jsonify({"error": "Record not found"}), 404

    soft_delete_record(cur, record_id)
    log_action(cur, g.user["user_id"], "record_deleted", f"Record #{record_id} soft-deleted")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": f"Record {record_id} deleted successfully"}), 200