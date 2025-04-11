from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'reservations.db')

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reservations (
                id INTEGER PRIMARY KEY,
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
        cursor = conn.execute("SELECT * FROM reservations WHERE id = ?", (gift_id,))
        if cursor.fetchone():
            return "Already reserved", 409
        conn.execute("INSERT INTO reservations (id, reservedBy) VALUES (?, ?)", (gift_id, reserved_by))
        return "Success", 200

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=5000)
