"""
analytics_routes.py
GET /api/analytics/summary   → income / expenses / net
GET /api/analytics/category  → by category
GET /api/analytics/monthly   → by month
GET /api/analytics/audit     → Admin: recent audit log entries
"""

from flask import Blueprint, jsonify, g, request
from extensions import mysql
from db import get_connection
from utils.decorators    import token_required, roles_required
from models.record_model import get_summary, get_category_breakdown, get_monthly_trends

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/summary", methods=["GET"])
@token_required
@roles_required("admin", "analyst")
def summary():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    row = get_summary(cur)

    cur.close()
    conn.close()

    total_income   = float(row["total_income"]   or 0)
    total_expenses = float(row["total_expenses"] or 0)

    return jsonify({
        "total_income":   round(total_income,   2),
        "total_expenses": round(total_expenses, 2),
        "net_balance":    round(total_income - total_expenses, 2)
    }), 200


@analytics_bp.route("/category", methods=["GET"])
@token_required
@roles_required("admin", "analyst")
def by_category():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    rows = get_category_breakdown(cur)
    cur.close()

    result = [
        {"category": r["category"], "type": r["type"], "total": float(r["total"])}
        for r in rows
    ]
    cur.close()
    conn.close()
    return jsonify({"breakdown": result, "count": len(result)}), 200


@analytics_bp.route("/monthly", methods=["GET"])
@token_required
@roles_required("admin", "analyst")
def monthly_trends():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    rows = get_monthly_trends(cur)

    cur.close()
    conn.close()

    result = [
        {"month": r["month"], "type": r["type"], "total": float(r["total"])}
        for r in rows
    ]
    return jsonify({"trends": result, "count": len(result)}), 200


@analytics_bp.route("/audit", methods=["GET"])
@token_required
@roles_required("admin")
def audit_log():
    """Admin only: recent 200 audit log entries."""
    try:
        limit = min(200, int(request.args.get("limit", 50)))
    except ValueError:
        limit = 50

    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT al.id, al.user_id, u.name AS user_name, al.action,
                  al.detail, al.ip_address, al.created_at
           FROM audit_logs al
           LEFT JOIN users u ON u.id = al.user_id
           ORDER BY al.created_at DESC
           LIMIT %s""",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    cur.close()

    for r in rows:
        if r.get("created_at"):
            r["created_at"] = str(r["created_at"])

    return jsonify({"logs": rows, "count": len(rows)}), 200