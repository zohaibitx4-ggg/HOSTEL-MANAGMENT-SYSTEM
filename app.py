"""
Hostel Management System - Backend

A small Flask server that
  1. serves the frontend (files inside /static)
  2. provides a REST API for students, rooms, bookings and fees
  3. stores everything in a SQLite database file (hostel.db)

Tables:
  students (id, name, roll_no, phone, department)
  rooms    (id, room_no, capacity, monthly_rent)
  bookings (id, student_id, room_id, check_in, check_out)
           -> a booking is "active" while check_out is empty
  fees     (id, student_id, month, amount, paid_on)
"""

import re
import sqlite3
from datetime import date

from flask import Flask, jsonify, request

app = Flask(__name__, static_folder="static", static_url_path="")
DB_FILE = "hostel.db"


# ---------- Database helpers ----------

def get_db():
    """Open a connection to the SQLite file."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row            # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # needed for ON DELETE CASCADE
    return conn


def init_db():
    """Create all tables if they do not exist yet."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS students (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                roll_no    TEXT NOT NULL UNIQUE,
                phone      TEXT NOT NULL,
                department TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rooms (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                room_no      TEXT NOT NULL UNIQUE,
                capacity     INTEGER NOT NULL CHECK (capacity > 0),
                monthly_rent INTEGER NOT NULL CHECK (monthly_rent >= 0)
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                room_id    INTEGER NOT NULL,
                check_in   TEXT NOT NULL,
                check_out  TEXT,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (room_id)    REFERENCES rooms(id)    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS fees (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                month      TEXT NOT NULL,
                amount     INTEGER NOT NULL CHECK (amount > 0),
                paid_on    TEXT NOT NULL,
                UNIQUE (student_id, month),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            );
            """
        )


def error(message, code=400):
    """Return a JSON error message."""
    return jsonify({"error": message}), code


def clean(data, key):
    """Get a text value from JSON and remove extra spaces."""
    return str(data.get(key) or "").strip()


def to_int(value):
    """Convert to int, or return None if it is not a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------- Frontend ----------

@app.route("/")
def home():
    return app.send_static_file("index.html")


# ---------- Dashboard ----------

@app.route("/api/dashboard")
def dashboard():
    """Summary numbers shown on the dashboard."""
    with get_db() as conn:
        students = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        rooms = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
        beds = conn.execute("SELECT COALESCE(SUM(capacity), 0) FROM rooms").fetchone()[0]
        occupied = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE check_out IS NULL"
        ).fetchone()[0]
        total_fees = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM fees"
        ).fetchone()[0]

    return jsonify(
        {
            "students": students,
            "rooms": rooms,
            "total_beds": beds,
            "occupied_beds": occupied,
            "available_beds": beds - occupied,
            "total_fees": total_fees,
        }
    )


# ---------- Students ----------

@app.route("/api/students", methods=["GET"])
def list_students():
    """All students, with their current room (if any)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.name, s.roll_no, s.phone, s.department,
                   r.room_no, r.monthly_rent
            FROM students s
            LEFT JOIN bookings b ON b.student_id = s.id AND b.check_out IS NULL
            LEFT JOIN rooms r    ON r.id = b.room_id
            ORDER BY s.id DESC
            """
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    name = clean(data, "name")
    roll_no = clean(data, "roll_no")
    phone = clean(data, "phone")
    department = clean(data, "department")

    if not (name and roll_no and phone and department):
        return error("Name, roll number, phone and department are required")

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO students (name, roll_no, phone, department) VALUES (?, ?, ?, ?)",
                (name, roll_no, phone, department),
            )
    except sqlite3.IntegrityError:
        return error("This roll number already exists", 409)
    return jsonify({"ok": True}), 201


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    """Delete a student (their bookings and fees are deleted too)."""
    with get_db() as conn:
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return jsonify({"ok": True})


# ---------- Rooms ----------

@app.route("/api/rooms", methods=["GET"])
def list_rooms():
    """All rooms, with occupied and available beds."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT r.id, r.room_no, r.capacity, r.monthly_rent,
                   COUNT(b.id) AS occupied
            FROM rooms r
            LEFT JOIN bookings b ON b.room_id = r.id AND b.check_out IS NULL
            GROUP BY r.id
            ORDER BY r.room_no
            """
        ).fetchall()

    rooms = []
    for r in rows:
        room = dict(r)
        room["available"] = room["capacity"] - room["occupied"]
        rooms.append(room)
    return jsonify(rooms)


@app.route("/api/rooms", methods=["POST"])
def add_room():
    data = request.get_json(silent=True) or {}
    room_no = clean(data, "room_no")
    capacity = to_int(data.get("capacity"))
    rent = to_int(data.get("monthly_rent"))

    if not room_no:
        return error("Room number is required")
    if capacity is None or capacity < 1:
        return error("Capacity must be at least 1")
    if rent is None or rent < 0:
        return error("Monthly rent must be a valid number")

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO rooms (room_no, capacity, monthly_rent) VALUES (?, ?, ?)",
                (room_no, capacity, rent),
            )
    except sqlite3.IntegrityError:
        return error("This room number already exists", 409)
    return jsonify({"ok": True}), 201


@app.route("/api/rooms/<int:room_id>", methods=["DELETE"])
def delete_room(room_id):
    """Delete a room, but only if nobody is living in it."""
    with get_db() as conn:
        active = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE room_id = ? AND check_out IS NULL",
            (room_id,),
        ).fetchone()[0]
        if active:
            return error("Room has students living in it. Check them out first.", 409)
        conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    return jsonify({"ok": True})


# ---------- Bookings ----------

@app.route("/api/bookings", methods=["GET"])
def list_bookings():
    """All bookings (newest first), active and past."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT b.id, s.name, s.roll_no, r.room_no,
                   b.check_in, b.check_out
            FROM bookings b
            JOIN students s ON s.id = b.student_id
            JOIN rooms r    ON r.id = b.room_id
            ORDER BY b.id DESC
            """
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/bookings", methods=["POST"])
def add_booking():
    """Book a room for a student. JSON: {"student_id": 1, "room_id": 2}"""
    data = request.get_json(silent=True) or {}
    student_id = to_int(data.get("student_id"))
    room_id = to_int(data.get("room_id"))

    with get_db() as conn:
        student = conn.execute(
            "SELECT id FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        room = conn.execute(
            "SELECT capacity FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
        if not student:
            return error("Student not found", 404)
        if not room:
            return error("Room not found", 404)

        # Rule 1: a student can have only one active room
        already = conn.execute(
            "SELECT 1 FROM bookings WHERE student_id = ? AND check_out IS NULL",
            (student_id,),
        ).fetchone()
        if already:
            return error("This student already has a room", 409)

        # Rule 2: the room must have a free bed
        occupied = conn.execute(
            "SELECT COUNT(*) FROM bookings WHERE room_id = ? AND check_out IS NULL",
            (room_id,),
        ).fetchone()[0]
        if occupied >= room["capacity"]:
            return error("This room is full", 409)

        conn.execute(
            "INSERT INTO bookings (student_id, room_id, check_in) VALUES (?, ?, ?)",
            (student_id, room_id, date.today().isoformat()),
        )
    return jsonify({"ok": True}), 201


@app.route("/api/bookings/<int:booking_id>/checkout", methods=["POST"])
def checkout(booking_id):
    """Check a student out of their room (frees the bed)."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE bookings SET check_out = ? WHERE id = ? AND check_out IS NULL",
            (date.today().isoformat(), booking_id),
        )
    if cur.rowcount == 0:
        return error("Active booking not found", 404)
    return jsonify({"ok": True})


# ---------- Fees ----------

@app.route("/api/fees", methods=["GET"])
def list_fees():
    """All fee payments (newest first)."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT f.id, s.name, s.roll_no, f.month, f.amount, f.paid_on
            FROM fees f
            JOIN students s ON s.id = f.student_id
            ORDER BY f.id DESC
            """
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/fees", methods=["POST"])
def add_fee():
    """Record a fee payment. JSON: {"student_id": 1, "month": "2026-10", "amount": 5000}"""
    data = request.get_json(silent=True) or {}
    student_id = to_int(data.get("student_id"))
    month = clean(data, "month")
    amount = to_int(data.get("amount"))

    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        return error("Month must look like 2026-10")
    if amount is None or amount <= 0:
        return error("Amount must be greater than 0")

    with get_db() as conn:
        student = conn.execute(
            "SELECT id FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        if not student:
            return error("Student not found", 404)

        try:
            conn.execute(
                "INSERT INTO fees (student_id, month, amount, paid_on) VALUES (?, ?, ?, ?)",
                (student_id, month, amount, date.today().isoformat()),
            )
        except sqlite3.IntegrityError:
            return error("Fee for this student and month is already recorded", 409)
    return jsonify({"ok": True}), 201


@app.route("/api/fees/<int:fee_id>", methods=["DELETE"])
def delete_fee(fee_id):
    with get_db() as conn:
        conn.execute("DELETE FROM fees WHERE id = ?", (fee_id,))
    return jsonify({"ok": True})


# ---------- Start the server ----------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
