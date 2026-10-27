// Frontend logic: talks to the Flask API using fetch().

// ---------------------------------------------------------
// Small helpers
// ---------------------------------------------------------

// Send a request to the backend and return { ok, data }
async function api(url, method = "GET", body = null) {
  const options = { method, headers: {} };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  const data = await res.json();
  return { ok: res.ok, data };
}

// Show a green (success) or red (error) message at the top
const messageBox = document.getElementById("message");
let messageTimer;

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.className = isError ? "error" : "";
  messageBox.hidden = false;
  clearTimeout(messageTimer);
  messageTimer = setTimeout(() => (messageBox.hidden = true), 4000);
}

// Create a button
function button(label, className, onClick) {
  const b = document.createElement("button");
  b.textContent = label;
  b.className = `small ${className}`;
  b.addEventListener("click", onClick);
  return b;
}

// Create a coloured badge
function badge(text, color) {
  const span = document.createElement("span");
  span.className = `badge ${color}`;
  span.textContent = text;
  return span;
}

// Create a table row. "values" can be text or elements. "buttons" go in the last cell.
function makeRow(values, buttons = []) {
  const tr = document.createElement("tr");
  values.forEach((value) => {
    const td = document.createElement("td");
    if (value instanceof Node) {
      td.appendChild(value);
    } else {
      td.textContent = value ?? "-"; // textContent keeps user input safe
    }
    tr.appendChild(td);
  });

  const actions = document.createElement("td");
  actions.className = "actions";
  buttons.forEach((b) => actions.appendChild(b));
  tr.appendChild(actions);
  return tr;
}

// Fill a table body with rows
function fillTable(tbodyId, rows) {
  const tbody = document.getElementById(tbodyId);
  tbody.innerHTML = "";
  rows.forEach((row) => tbody.appendChild(row));
}

// Fill a <select> with options
function fillSelect(selectId, items, placeholder) {
  const select = document.getElementById(selectId);
  select.innerHTML = "";

  const first = document.createElement("option");
  first.value = "";
  first.textContent = placeholder;
  select.appendChild(first);

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  });
}

// ---------------------------------------------------------
// Tabs
// ---------------------------------------------------------

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = true));
    tab.classList.add("active");
    document.getElementById(`tab-${tab.dataset.tab}`).hidden = false;
  });
});

// ---------------------------------------------------------
// Load everything and draw it on the page
// ---------------------------------------------------------

let students = []; // kept so the fee form can look up room rent

async function loadAll() {
  const [dash, stu, rooms, bookings, fees] = await Promise.all([
    api("/api/dashboard"),
    api("/api/students"),
    api("/api/rooms"),
    api("/api/bookings"),
    api("/api/fees"),
  ]);

  students = stu.data;
  drawDashboard(dash.data);
  drawStudents(stu.data);
  drawRooms(rooms.data);
  drawBookings(bookings.data);
  drawFees(fees.data);
  drawDropdowns(stu.data, rooms.data);
}

function drawDashboard(d) {
  document.getElementById("stat-students").textContent = d.students;
  document.getElementById("stat-rooms").textContent = d.rooms;
  document.getElementById("stat-beds").textContent = d.total_beds;
  document.getElementById("stat-occupied").textContent = d.occupied_beds;
  document.getElementById("stat-available").textContent = d.available_beds;
  document.getElementById("stat-fees").textContent = d.total_fees;
}

function drawStudents(list) {
  fillTable(
    "students-table",
    list.map((s) =>
      makeRow(
        [
          s.roll_no,
          s.name,
          s.phone,
          s.department,
          s.room_no ? badge(s.room_no, "green") : badge("No room", "grey"),
        ],
        [button("Delete", "danger", () => deleteStudent(s.id))]
      )
    )
  );
}

function drawRooms(list) {
  fillTable(
    "rooms-table",
    list.map((r) =>
      makeRow(
        [
          r.room_no,
          r.capacity,
          r.occupied,
          r.available,
          r.monthly_rent,
          r.available > 0 ? badge("Available", "green") : badge("Full", "red"),
        ],
        [button("Delete", "danger", () => deleteRoom(r.id))]
      )
    )
  );
}

function drawBookings(list) {
  fillTable(
    "bookings-table",
    list.map((b) => {
      const buttons = b.check_out
        ? []
        : [button("Check out", "warn", () => checkoutBooking(b.id))];
      return makeRow(
        [b.name, b.roll_no, b.room_no, b.check_in, b.check_out || badge("Living", "green")],
        buttons
      );
    })
  );
}

function drawFees(list) {
  fillTable(
    "fees-table",
    list.map((f) =>
      makeRow(
        [f.name, f.roll_no, f.month, f.amount, f.paid_on],
        [button("Delete", "danger", () => deleteFee(f.id))]
      )
    )
  );
}

function drawDropdowns(studentList, roomList) {
  // Booking form: only students without a room, only rooms with a free bed
  fillSelect(
    "b-student",
    studentList
      .filter((s) => !s.room_no)
      .map((s) => ({ value: s.id, label: `${s.name} (${s.roll_no})` })),
    "Select student"
  );
  fillSelect(
    "b-room",
    roomList
      .filter((r) => r.available > 0)
      .map((r) => ({ value: r.id, label: `${r.room_no} (${r.available} free)` })),
    "Select room"
  );

  // Fee form: all students
  fillSelect(
    "f-student",
    studentList.map((s) => ({ value: s.id, label: `${s.name} (${s.roll_no})` })),
    "Select student"
  );
}

// ---------------------------------------------------------
// Actions (every action reloads the page data at the end)
// ---------------------------------------------------------

// Send a form to the backend, show a message, then reload
async function submitForm(form, url, body, successText) {
  const result = await api(url, "POST", body);
  if (!result.ok) {
    showMessage(result.data.error, true);
    return;
  }
  form.reset();
  showMessage(successText);
  loadAll();
}

// Students
document.getElementById("student-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitForm(
    e.target,
    "/api/students",
    {
      name: document.getElementById("s-name").value,
      roll_no: document.getElementById("s-roll").value,
      phone: document.getElementById("s-phone").value,
      department: document.getElementById("s-dept").value,
    },
    "Student added"
  );
});

async function deleteStudent(id) {
  if (!confirm("Delete this student with their bookings and fee record?")) return;
  await api(`/api/students/${id}`, "DELETE");
  showMessage("Student deleted");
  loadAll();
}

// Rooms
document.getElementById("room-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitForm(
    e.target,
    "/api/rooms",
    {
      room_no: document.getElementById("r-no").value,
      capacity: document.getElementById("r-cap").value,
      monthly_rent: document.getElementById("r-rent").value,
    },
    "Room added"
  );
});

async function deleteRoom(id) {
  if (!confirm("Delete this room?")) return;
  const result = await api(`/api/rooms/${id}`, "DELETE");
  if (!result.ok) {
    showMessage(result.data.error, true);
    return;
  }
  showMessage("Room deleted");
  loadAll();
}

// Bookings
document.getElementById("booking-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitForm(
    e.target,
    "/api/bookings",
    {
      student_id: document.getElementById("b-student").value,
      room_id: document.getElementById("b-room").value,
    },
    "Room booked"
  );
});

async function checkoutBooking(id) {
  if (!confirm("Check this student out of the room?")) return;
  const result = await api(`/api/bookings/${id}/checkout`, "POST");
  if (!result.ok) {
    showMessage(result.data.error, true);
    return;
  }
  showMessage("Student checked out");
  loadAll();
}

// Fees
document.getElementById("fee-form").addEventListener("submit", (e) => {
  e.preventDefault();
  submitForm(
    e.target,
    "/api/fees",
    {
      student_id: document.getElementById("f-student").value,
      month: document.getElementById("f-month").value,
      amount: document.getElementById("f-amount").value,
    },
    "Payment saved"
  );
});

// When a student is picked, fill the amount with their room rent
document.getElementById("f-student").addEventListener("change", (e) => {
  const student = students.find((s) => String(s.id) === e.target.value);
  if (student && student.monthly_rent) {
    document.getElementById("f-amount").value = student.monthly_rent;
  }
});

async function deleteFee(id) {
  if (!confirm("Delete this payment record?")) return;
  await api(`/api/fees/${id}`, "DELETE");
  showMessage("Payment deleted");
  loadAll();
}

// Load data when the page first opens
loadAll();
