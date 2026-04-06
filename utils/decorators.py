"""
decorators.py — JWT auth + RBAC decorators.
"""

from functools import wraps
from flask import request, jsonify, g
import jwt
from utils.auth_utils import decode_token


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.split(" ")[1] if auth_header.startswith("Bearer ") else None
        if not token:
            return jsonify({"error": "Authentication token is missing"}), 401
        try:
            g.user = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired. Please login again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please login again."}), 401
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.user.get("role") not in roles:
                return jsonify({
                    "error": f"Access denied. Required role(s): {', '.join(roles)}"
                }), 403
            return f(*args, **kwargs)
        return decorated
    return decorator