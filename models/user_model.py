"""
user_model.py — SQL helpers for the `users` table.
"""

def get_user_by_email(cursor, email):
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    return cursor.fetchone()


def get_user_by_id(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchone()


def get_all_users(cursor):
    cursor.execute("SELECT id, name, email, role, status, created_at FROM users ORDER BY id DESC")
    return cursor.fetchall()


def create_user(cursor, name, email, hashed_password, role="viewer"):
    cursor.execute(
        "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
        (name, email, hashed_password, role)
    )


def update_user_role_status(cursor, user_id, role=None, status=None):
    if role and status:
        cursor.execute("UPDATE users SET role=%s, status=%s WHERE id=%s", (role, status, user_id))
    elif role:
        cursor.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
    elif status:
        cursor.execute("UPDATE users SET status=%s WHERE id=%s", (status, user_id))


def update_user_password(cursor, user_id, hashed_password):
    cursor.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_password, user_id))