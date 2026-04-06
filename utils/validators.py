"""
validators.py — Input validation helpers.
"""

import re
from datetime import datetime

VALID_ROLES    = {"admin", "analyst", "viewer"}
VALID_STATUSES = {"active", "inactive"}
VALID_TYPES    = {"income", "expense"}


def validate_registration(data: dict):
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip()
    password = data.get("password", "")
    if not name:
        return False, "Name is required"
    if not email or not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False, "A valid email is required"
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    return True, None


def validate_role(role: str):
    if role not in VALID_ROLES:
        return False, f"Role must be one of: {', '.join(sorted(VALID_ROLES))}"
    return True, None


def validate_status(status: str):
    if status not in VALID_STATUSES:
        return False, f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}"
    return True, None


def validate_record(data: dict):
    amount   = data.get("amount")
    rec_type = data.get("type", "").strip()
    category = data.get("category", "").strip()
    date_str = data.get("date", "").strip()

    if amount is None:
        return False, "Amount is required"
    try:
        if float(amount) <= 0:
            return False, "Amount must be a positive number"
    except (TypeError, ValueError):
        return False, "Amount must be a number"
    if rec_type not in VALID_TYPES:
        return False, f"Type must be one of: {', '.join(VALID_TYPES)}"
    if not category:
        return False, "Category is required"
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, "Date must be in YYYY-MM-DD format"
    return True, None