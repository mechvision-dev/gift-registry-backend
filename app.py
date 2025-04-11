from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Allow multiple reservations per gift
GIFT_LIMITS = {
    1: 3,   # Swaddelini
    3: 2,   # Change Mat
    4: 30   # Nappies
    # Default fallback is 1 for all others
}

DB_PATH = os.path.join(os.path.dirname(__file__), 'reservations.db')


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER,
                reservedBy TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')


def format_name(name):
    """Standardizes name casing: '  joHn   SMITH ' -> 'John Smith'"""
    return ' '.join(w.capitalize() for w in name.strip().split())


@app.route('/', methods=['GET'])
def get_reservations():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, reservedBy FROM reservations")
        result = [{"id": row[0], "reservedBy": row[1]} for row in cursor.fetchall()]
        return jsonify(result)


@app.route('/', methods=['POST'])
def reserve():
    data = request.get_json()
    gift_id = data.get("id")
    reserved_by = data.get("reservedBy")

    if not gift_id or not reserved_by:
        return "Invalid data", 400

    reserved_by = format_name(reserved_by)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM reservations WHERE id = ?", (gift_id,))
        count = cursor.fetchone()[0]
        max_allowed = GIFT_LIMITS.get(gift_id, 1)

        if count >= max_allowed:
            return "All spots for this gift are reserved", 409

        conn.execute("INSERT INTO reservations (id, reservedBy) VALUES (?, ?)", (gift_id, reserved_by))
        return "Success", 200


@app.route('/unreserve', methods=['POST'])
def unreserve():
    data = request.get_json()
    gift_id = data.get("id")
    reserved_by = data.get("reservedBy")

    if not gift_id or not reserved_by:
        return "Invalid data", 400

    reserved_by = format_name(reserved_by)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM reservations WHERE entry_id IN (SELECT entry_id FROM reservations WHERE id = ? AND reservedBy = ? LIMIT 1)", (gift_id, reserved_by))
        conn.commit()

    return "Reservation removed", 200


@app.route('/admin-data')
def admin_data():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, reservedBy, timestamp FROM reservations ORDER BY id ASC")
        grouped = {}
        for gift_id, name, ts in cursor.fetchall():
            grouped.setdefault(gift_id, []).append({"name": name, "timestamp": ts})
    return jsonify(grouped)


@app.route('/summary')
def reservation_summary():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, COUNT(*) as total FROM reservations GROUP BY id")
        result = {row[0]: row[1] for row in cursor.fetchall()}
    return jsonify(result)


@app.route('/debug-reservations')
def debug_reservations():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT * FROM reservations")
        rows = [{"entry_id": row[0], "id": row[1], "reservedBy": row[2], "timestamp": row[3]} for row in cursor.fetchall()]
    return jsonify(rows)


@app.route('/migrate-reservations-table')
def migrate_reservations_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS new_reservations (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id INTEGER,
                    reservedBy TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('INSERT INTO new_reservations (id, reservedBy, timestamp) SELECT id, reservedBy, datetime("now") FROM reservations')
            cursor.execute('DROP TABLE reservations')
            cursor.execute('ALTER TABLE new_reservations RENAME TO reservations')
            conn.commit()
        return "Migration successful! Table now includes timestamp.", 200
    except Exception as e:
        return f"Migration failed: {e}", 500


if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000)
