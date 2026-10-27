# Hostel Management System

A small full-stack project to manage a hostel: student records, rooms and availability, room booking, and fee records. It is written to be simple and easy to understand.

| Layer    | Technology                | File(s) |
|----------|---------------------------|---------|
| Frontend | HTML, CSS, JavaScript     | `static/index.html`, `static/style.css`, `static/script.js` |
| Backend  | Python + Flask (REST API) | `app.py` |
| Database | SQLite                    | `hostel.db` (created automatically) |

## Features

- **Dashboard:** total students, rooms, beds, occupied beds, available beds and fees collected
- **Students:** add and delete students (name, roll number, phone, department) and see their current room
- **Rooms:** add rooms with capacity and monthly rent, see occupied and available beds, and whether a room is Available or Full
- **Room booking:** book a room for a student, check a student out, and keep a full booking history
- **Fees:** record monthly fee payments (amount is filled from the room rent) and see all payments

## Rules the system follows

- A student can have only one active room at a time
- A room cannot be booked when it is full
- A room cannot be deleted while students are living in it
- Roll numbers and room numbers must be unique
- Fee for the same student and month can be saved only once
- Deleting a student also deletes their bookings and fee records

## How it works

```
Browser (HTML/JS)  --fetch-->  Flask API (app.py)  --SQL-->  SQLite (hostel.db)
```

## Database

```
students              rooms                 bookings                 fees
--------              -----                 --------                 ----
id (PK)  <-----+  +-> id (PK)               id (PK)                  id (PK)
name           |  |   room_no (unique)      student_id (FK) ---+     student_id (FK)
roll_no (uniq) |  |   capacity               room_id (FK) -----+     month
phone          |  |   monthly_rent           check_in               amount
department     |  |                          check_out (empty =     paid_on
               |  |                          still living)
               +--+--------------------------------------------+
```

- One student has many bookings (over time) and many fee payments
- One room has many bookings
- Free beds of a room = `capacity - active bookings`

## API endpoints

| Method | URL                              | What it does |
|--------|----------------------------------|--------------|
| GET    | `/api/dashboard`                 | Summary numbers |
| GET    | `/api/students`                  | List students with current room |
| POST   | `/api/students`                  | Add a student |
| DELETE | `/api/students/<id>`             | Delete a student |
| GET    | `/api/rooms`                     | List rooms with occupied / available beds |
| POST   | `/api/rooms`                     | Add a room |
| DELETE | `/api/rooms/<id>`                | Delete a room |
| GET    | `/api/bookings`                  | List all bookings |
| POST   | `/api/bookings`                  | Book a room (`{"student_id": 1, "room_id": 2}`) |
| POST   | `/api/bookings/<id>/checkout`    | Check a student out |
| GET    | `/api/fees`                      | List fee payments |
| POST   | `/api/fees`                      | Add a payment (`{"student_id": 1, "month": "2026-10", "amount": 5000}`) |
| DELETE | `/api/fees/<id>`                 | Delete a payment |

## Run it

You need Python 3.8+ installed.

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd hostel-management

# 2. (Optional) create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the app
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Suggested first steps: add a room, add a student, book the room, then record a fee.

## Project structure

```
hostel-management/
├── app.py            # Backend + database code
├── requirements.txt  # Python dependencies
├── .gitignore
├── README.md
└── static/           # Frontend
    ├── index.html
    ├── style.css
    └── script.js
```

## Ideas to extend it

- Admin login
- Show which students have not paid the current month
- Search and filter students
- Print a fee receipt
