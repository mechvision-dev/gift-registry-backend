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
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                id INTEGER,
                reservedBy TEXT
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
    """
    Handles the reservation of a gift by a user.
    This function processes a reservation request by extracting the gift ID and the user
    making the reservation from the request payload. It validates the input, ensures that
    the user-provided name is standardized, and checks if the maximum allowed reservations
    for the gift have been reached. If the reservation is valid, it stores the reservation
    in the database.
    Returns:
        tuple: A tuple containing a response message (str) and an HTTP status code (int).
            - "Invalid data", 400: If the input data is missing or invalid.
            - "All spots for this gift are reserved", 409: If the maximum allowed reservations
              for the gift have been reached.
            - "Success", 200: If the reservation is successfully created.
    Raises:
        sqlite3.Error: If there is an issue with the database operation.
    Notes:
        - The `reservedBy` field in the request payload is standardized to capitalize each word.
        - The maximum allowed reservations for a gift are determined by the `GIFT_LIMITS` dictionary.
        - The database connection is managed using a context manager to ensure proper cleanup.
    """
    data = request.get_json()
    gift_id = data.get("id")
    reserved_by = data.get("reservedBy")

    if not gift_id or not reserved_by:
        return "Invalid data", 400

    # Standardize the reserved_by input
    reserved_by = format_name(reserved_by)


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

            # Step 1: Create new schema with auto-incrementing entry_id
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS new_reservations (
                    entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    id INTEGER,
                    reservedBy TEXT
                )
            ''')

            # Step 2: Copy old data
            cursor.execute('INSERT INTO new_reservations (id, reservedBy) SELECT id, reservedBy FROM reservations')

            # Step 3: Replace the old table
            cursor.execute('DROP TABLE reservations')
            cursor.execute('ALTER TABLE new_reservations RENAME TO reservations')

            conn.commit()
        return "Migration successful! Schema now allows duplicate gift IDs.", 200
    except Exception as e:
        return f"Migration failed: {e}", 500

    
@app.route('/admin-data')
def admin_data():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT id, reservedBy FROM reservations ORDER BY id ASC")
        grouped = {}
        for gift_id, name in cursor.fetchall():
            grouped.setdefault(gift_id, []).append(name)
    return jsonify(grouped)

@app.route('/unreserve', methods=['POST'])
def unreserve():
    data = request.get_json()
    gift_id = data.get("id")
    reserved_by = data.get("reservedBy")

    if not gift_id or not reserved_by:
        return "Invalid data", 400

    # Normalize name
    reserved_by = format_name(reserved_by)


    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM reservations WHERE id = ? AND reservedBy = ?", (gift_id, reserved_by))
        conn.commit()
    return "Reservation removed", 200

    
if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000)
