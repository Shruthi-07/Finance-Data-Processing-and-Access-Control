"""
auth_routes.py
──────────────
POST /api/auth/register  → create account (default role = viewer)
POST /api/auth/login     → returns JWT token
"""

from flask import Blueprint, request, jsonify
from utils.auth_utils import hash_password, check_password, generate_token
from utils.validators import validate_registration
from models.user_model import get_user_by_email, create_user
from db import get_connection   

auth_bp = Blueprint("auth", __name__)


# ── Register ──────────────────────────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Public endpoint — anyone can self-register.
    Default role is 'viewer'. Admin upgrades roles later.

    Request body (JSON):
        { "name": "Alice", "email": "alice@example.com", "password": "secret123" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    # ── Validate input ────────────────────────────────────────
    is_valid, error = validate_registration(data)
    if not is_valid:
        return jsonify({"error": error}), 422

    name     = data["name"].strip()
    email    = data["email"].strip().lower()
    password = data["password"]
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    # ── Check duplicate email ─────────────────────────────────
    existing = get_user_by_email(cur, email)
    if existing:
        cur.close()
        return jsonify({"error": "Email already registered"}), 409

    # ── Hash password & insert ────────────────────────────────
    hashed = hash_password(password)
    create_user(cur, name, email, hashed, role="viewer")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Registration successful. Default role: viewer."}), 201


# ── Login ─────────────────────────────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Returns a JWT token on success.

    Request body (JSON):
        { "email": "alice@example.com", "password": "secret123" }

    Response (200):
        { "token": "<jwt>", "role": "viewer", "name": "Alice" }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 422
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    user = get_user_by_email(cur, email)
    cur.close()
    conn.close()

    # ── User not found ────────────────────────────────────────
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    # ── Account inactive ──────────────────────────────────────
    if user["status"] == "inactive":
        return jsonify({"error": "Your account has been deactivated. Contact admin."}), 403

    # ── Wrong password ────────────────────────────────────────
    if not check_password(password, user["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    # ── Generate token ────────────────────────────────────────
    token = generate_token(user["id"], user["role"])

    return jsonify({
        "message": "Login successful",
        "token":   token,
        "name": user["name"],
        "role": user["role"],
        "user": {
            "id":   user["id"],
            "name": user["name"],
            "role": user["role"]
        }
    }), 200

@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """
    Simple password reset (no OTP).
    User provides email + new password.
    """

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    email = data.get("email", "").strip().lower()
    new_password = data.get("new_password", "")

    if not email or not new_password:
        return jsonify({"error": "Email and new password are required"}), 422

    if len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 422
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    user = get_user_by_email(cur, email)
    if not user:
        cur.close()
        return jsonify({"error": "User not found"}), 404

    # 🔐 Hash new password
    hashed = hash_password(new_password)

    # Update password
    from models.user_model import update_user_password
    update_user_password(cur, user["id"], hashed)

    conn.commit()
    cur.close()

    return jsonify({"message": "Password reset successful"}), 200