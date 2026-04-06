"""
audit.py — Write entries to the audit_logs table.
"""

from flask import request


def log_action(cursor, user_id: int, action: str, detail: str = ""):
    """Insert an audit log row. Silently swallows errors so it never breaks a request."""
    try:
        ip = request.remote_addr or "unknown"
        cursor.execute(
            "INSERT INTO audit_logs (user_id, action, detail, ip_address) VALUES (%s, %s, %s, %s)",
            (user_id, action, detail, ip)
        )
    except Exception:
        pass