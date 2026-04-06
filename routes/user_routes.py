"""
user_routes.py — Admin-only user management.
GET    /api/users/      → list all users
POST   /api/users/      → create user (any role)
GET    /api/users/<id>  → single user
PATCH  /api/users/<id>  → update role / status
"""

from flask import Blueprint, request, jsonify, g
from extensions import mysql
from db import get_connection   
from utils.decorators  import token_required, roles_required
from utils.auth_utils  import hash_password
from utils.validators  import validate_registration, validate_role, validate_status
from utils.audit       import log_action
from models.user_model import (
    get_all_users, get_user_by_id, get_user_by_email,
    create_user, update_user_role_status
)

user_bp = Blueprint("users", __name__)


@user_bp.route("/", methods=["GET"])
@token_required
@roles_required("admin")
def list_users():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    users = get_all_users(cur)
    cur.close()
    conn.close()
    for u in users:
        if u.get("created_at"):
            u["created_at"] = str(u["created_at"])
    return jsonify({"users": users, "count": len(users)}), 200


@user_bp.route("/<int:user_id>", methods=["GET"])
@token_required
@roles_required("admin")
def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    user = get_user_by_id(cur, user_id)
    cur.close()
    conn.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.pop("password", None)
    if user.get("created_at"):
        user["created_at"] = str(user["created_at"])
    return jsonify({"user": user}), 200


@user_bp.route("/", methods=["POST"])
@token_required
@roles_required("admin")
def create_user_admin():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    is_valid, error = validate_registration(data)
    if not is_valid:
        return jsonify({"error": error}), 422

    role = data.get("role", "viewer").strip()
    is_valid, error = validate_role(role)
    if not is_valid:
        return jsonify({"error": error}), 422

    name  = data["name"].strip()
    email = data["email"].strip().lower()
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if get_user_by_email(cur, email):
        cur.close()
        return jsonify({"error": "Email already registered"}), 409

    hashed = hash_password(data["password"])
    create_user(cur, name, email, hashed, role=role)
    conn.commit()
    new_user = get_user_by_email(cur, email)
    log_action(cur, g.user["user_id"], "user_created",
               f"Admin created user {email} with role {role}")
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": f"User '{name}' created with role '{role}'."}), 201


@user_bp.route("/<int:user_id>", methods=["PATCH"])
@token_required
@roles_required("admin")
def update_user(user_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    role   = data.get("role")
    status = data.get("status")

    if not role and not status:
        return jsonify({"error": "Provide at least one of: role, status"}), 422

    if role:
        is_valid, error = validate_role(role)
        if not is_valid:
            return jsonify({"error": error}), 422

    if status:
        is_valid, error = validate_status(status)
        if not is_valid:
            return jsonify({"error": error}), 422
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    user = get_user_by_id(cur, user_id)
    if not user:
        cur.close()
        return jsonify({"error": "User not found"}), 404

    if user_id == g.user["user_id"] and status == "inactive":
        cur.close()
        return jsonify({"error": "You cannot deactivate your own account"}), 403

    update_user_role_status(cur, user_id, role=role, status=status)
    log_action(cur, g.user["user_id"], "user_updated",
               f"Updated user {user_id}: role={role}, status={status}")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": f"User {user_id} updated successfully."}), 200