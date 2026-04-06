"""
record_model.py — SQL helpers for the `records` table.
Soft-delete: records are marked status='deleted', never hard-deleted.
"""


def create_record(cursor, user_id, amount, rec_type, category, date, description=""):
    cursor.execute(
        """INSERT INTO records (user_id, amount, type, category, date, description)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_id, amount, rec_type, category, date, description)
    )
    return cursor.lastrowid


def _build_filter_query(base: str, params: list, rec_type=None, category=None,
                        date_from=None, date_to=None, search=None):
    if rec_type:
        base += " AND type = %s";         params.append(rec_type)
    if category:
        base += " AND category LIKE %s";  params.append(f"%{category}%")
    if date_from:
        base += " AND date >= %s";        params.append(date_from)
    if date_to:
        base += " AND date <= %s";        params.append(date_to)
    if search:
        base += " AND (category LIKE %s OR description LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    return base, params


def count_all_records(cursor, rec_type=None, category=None,
                      date_from=None, date_to=None, search=None):
    q, p = _build_filter_query(
        "SELECT COUNT(*) AS cnt FROM records WHERE status='active'",
        [], rec_type, category, date_from, date_to, search
    )
    cursor.execute(q, p)
    return cursor.fetchone()["cnt"]


def count_records_by_user(cursor, user_id, rec_type=None, category=None,
                          date_from=None, date_to=None, search=None):
    q, p = _build_filter_query(
        "SELECT COUNT(*) AS cnt FROM records WHERE status='active' AND user_id=%s",
        [user_id], rec_type, category, date_from, date_to, search
    )
    cursor.execute(q, p)
    return cursor.fetchone()["cnt"]


def get_all_records(cursor, rec_type=None, category=None,
                    date_from=None, date_to=None, search=None,
                    page=1, limit=20):
    offset = (page - 1) * limit
    q, p = _build_filter_query(
        "SELECT * FROM records WHERE status='active'",
        [], rec_type, category, date_from, date_to, search
    )
    q += " ORDER BY date DESC, id DESC LIMIT %s OFFSET %s"
    p += [limit, offset]
    cursor.execute(q, p)
    return cursor.fetchall()


def get_records_by_user(cursor, user_id, rec_type=None, category=None,
                        date_from=None, date_to=None, search=None,
                        page=1, limit=20):
    offset = (page - 1) * limit
    q, p = _build_filter_query(
        "SELECT * FROM records WHERE status='active' AND user_id=%s",
        [user_id], rec_type, category, date_from, date_to, search
    )
    q += " ORDER BY date DESC, id DESC LIMIT %s OFFSET %s"
    p += [limit, offset]
    cursor.execute(q, p)
    return cursor.fetchall()


def get_record_by_id(cursor, record_id):
    cursor.execute("SELECT * FROM records WHERE id=%s AND status='active'", (record_id,))
    return cursor.fetchone()


def update_record(cursor, record_id, amount, rec_type, category, date, description):
    cursor.execute(
        """UPDATE records
           SET amount=%s, type=%s, category=%s, date=%s, description=%s
           WHERE id=%s AND status='active'""",
        (amount, rec_type, category, date, description, record_id)
    )


def soft_delete_record(cursor, record_id):
    """Mark record as deleted instead of hard-deleting."""
    cursor.execute(
        "UPDATE records SET status='deleted' WHERE id=%s",
        (record_id,)
    )

def get_summary(cursor):
    query = """
        SELECT 
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS total_income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS total_expenses
        FROM records
        WHERE status='active'
    """
    cursor.execute(query)
    return cursor.fetchone()


def get_category_breakdown(cursor):
    query = """
        SELECT category, type, SUM(amount) AS total
        FROM records
        WHERE status='active'
        GROUP BY category, type
        ORDER BY total DESC
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_monthly_trends(cursor):
    query = """
        SELECT DATE_FORMAT(date, '%%Y-%%m') AS month,
               type,
               SUM(amount) AS total
        FROM records
        WHERE status='active'
        GROUP BY month, type
        ORDER BY month ASC
    """
    cursor.execute(query)
    return cursor.fetchall()


def get_all_records_for_export(cursor, user_id=None):
    q = "SELECT * FROM records WHERE status='active'"
    p = []
    if user_id:
        q += " AND user_id=%s"; p.append(user_id)
    q += " ORDER BY date DESC"
    cursor.execute(q, p)
    return cursor.fetchall()