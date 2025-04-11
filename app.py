from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

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
                id INTEGER,
                reservedBy TEXT
            )
        ''')

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

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT reservedBy FROM reservations WHERE id = ?", (gift_id,))
        existing = [row[0] for row in cursor.fetchall()]
        max_allowed = GIFT_LIMITS.get(gift_id, 1)

        if len(existing) >= max_allowed:
            return "All spots for this gift are reserved", 409

        conn.execute("INSERT INTO reservations (id, reservedBy) VALUES (?, ?)", (gift_id, reserved_by))
        return "Success", 200
    
@app.route('/debug-reservations')
def debug_reservations():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, reservedBy FROM reservations")
        rows = [{"id": row[0], "reservedBy": row[1]} for row in cursor.fetchall()]
    return jsonify(rows)

@app.route("/migrate-reservations-table")
def migrate_reservations_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Step 1: Create the new schema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS new_reservations (
                    id INTEGER,
                    reservedBy TEXT
                )
            ''')

            # Step 2: Copy old data
            cursor.execute('INSERT INTO new_reservations SELECT id, reservedBy FROM reservations')

            # Step 3: Replace the old table
            cursor.execute('DROP TABLE reservations')
            cursor.execute('ALTER TABLE new_reservations RENAME TO reservations')

            conn.commit()
        return "Migration successful! The reservations table now supports multiple entries per gift.", 200
    except Exception as e:
        return f"Migration failed: {e}", 500

    
if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000)
