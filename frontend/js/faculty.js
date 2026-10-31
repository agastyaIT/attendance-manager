const faculty = requireLogin("faculty");

let classes = [];
let current = null; // the session that is open on the page

if (faculty) {
  document.getElementById("whoami").textContent = faculty.name;
  document.getElementById("logout-btn").addEventListener("click", logout);
  setupSessionForm();
  setupSessionButtons();
  run(loadAll);
}

async function run(action) {
  try {
    await action();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

// ---------- small helpers ----------
function todayISO() {
  const d = new Date();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return d.getFullYear() + "-" + month + "-" + day;
}

function formatDate(iso) {
  const parts = iso.split("-");
  return parts[2] + "/" + parts[1] + "/" + parts[0];
}

function shortTime(t) {
  return t.slice(0, 5);
}

function classLabel(c) {
  return c.subject_code + " - " + c.subject_name + " (Section " + c.section + ")";
}

async function loadAll() {
  await loadClasses();
  await loadSessions();
}

// ---------- choosing a class and starting a session ----------
async function loadClasses() {
  const data = await apiFetch("/faculty/classes");
  classes = data.classes;

  const form = document.getElementById("session-form");
  const note = document.getElementById("no-classes");

  if (classes.length === 0) {
    form.hidden = true;
    note.hidden = false;
    return;
  }

  note.hidden = true;
  form.hidden = false;
  fillSelect("class-select", classes, (c) => c.subject_id + "-" + c.section, classLabel);
}

function setupSessionForm() {
  const dateInput = document.getElementById("session-date");
  dateInput.value = todayISO();
  dateInput.max = todayISO();
  document.getElementById("start-time").value = "09:00";
  document.getElementById("end-time").value = "10:00";

  document.getElementById("session-form").addEventListener("submit", (event) => {
    event.preventDefault();
    hideMessage();

    run(async () => {
      const parts = document.getElementById("class-select").value.split("-");
      const subjectId = Number(parts[0]);
      const section = parts[1];
      const chosen = classes.find((c) => c.subject_id === subjectId && c.section === section);

      const data = await apiFetch("/faculty/attendance-sessions", {
        method: "POST",
        body: JSON.stringify({
          subject_id: subjectId,
          section: section,
          session_date: dateInput.value,
          start_time: document.getElementById("start-time").value,
          end_time: document.getElementById("end-time").value,
        }),
      });

      await openSession(data.session.id, classLabel(chosen));
      await loadSessions();
      showMessage("Session created. Tick the students who are present.", "success");
    });
  });
}

// ---------- the open session (roster) ----------
async function openSession(id, title) {
  const data = await apiFetch("/faculty/attendance-sessions/" + id + "/students");
  current = { id: id, title: title };
  renderSession(data);
  document.getElementById("session-panel").scrollIntoView({ behavior: "smooth" });
}

function renderSession(data) {
  const session = data.session;
  const finalized = session.status === "finalized";
  const empty = data.students.length === 0;

  document.getElementById("session-panel").hidden = false;
  document.getElementById("session-title").textContent = current.title;
  document.getElementById("session-info").textContent =
    "Section " + session.section + " | " + formatDate(session.session_date) +
    " | " + shortTime(session.start_time) + " - " + shortTime(session.end_time) + " ";

  const badge = document.getElementById("session-status");
  badge.textContent = session.status;
  badge.className = "badge " + session.status;

  document.getElementById("finalized-note").hidden = !finalized;
  document.getElementById("empty-note").hidden = !empty;
  document.getElementById("roster-tools").hidden = finalized || empty;
  document.getElementById("roster-actions").hidden = finalized || empty;

  const body = document.getElementById("roster-body");
  body.replaceChildren();

  data.students.forEach((student) => {
    const box = document.createElement("input");
    box.type = "checkbox";
    box.dataset.id = student.student_id;
    box.checked = student.status === "present";
    box.disabled = finalized;
    box.setAttribute("aria-label", "Present: " + student.name);
    box.addEventListener("change", updateCount);

    const boxCell = document.createElement("td");
    boxCell.className = "check-col";
    boxCell.append(box);

    const row = document.createElement("tr");
    row.append(boxCell, cell(student.name), cell(student.email));
    body.append(row);
  });

  updateCount();
}

function checkboxes() {
  return Array.from(document.querySelectorAll("#roster-body input[type=checkbox]"));
}

function updateCount() {
  const boxes = checkboxes();
  const present = boxes.filter((b) => b.checked).length;
  document.getElementById("count").textContent =
    "Present: " + present + " of " + boxes.length;
}

function setAll(value) {
  checkboxes().forEach((b) => (b.checked = value));
  updateCount();
}

// One entry for every student, so nobody is left unmarked.
function collectRecords() {
  return checkboxes().map((b) => ({
    student_id: Number(b.dataset.id),
    status: b.checked ? "present" : "absent",
  }));
}

async function saveRecords() {
  await apiFetch("/faculty/attendance-sessions/" + current.id + "/records", {
    method: "PUT",
    body: JSON.stringify({ records: collectRecords() }),
  });
}

async function finalizeCurrent() {
  const records = collectRecords();
  const present = records.filter((r) => r.status === "present").length;
  const absent = records.length - present;

  const ok = confirm(
    "Finalize this session?\n\nPresent: " + present + "\nAbsent: " + absent +
    "\n\nAfter finalizing you cannot change it. Only an administrator can correct it."
  );
  if (!ok) return;

  await saveRecords();
  await apiFetch("/faculty/attendance-sessions/" + current.id + "/finalize", { method: "POST" });
  await openSession(current.id, current.title);
  await loadSessions();
  showMessage("Session finalized", "success");
}

function setupSessionButtons() {
  document.getElementById("select-all").addEventListener("click", () => setAll(true));
  document.getElementById("clear-all").addEventListener("click", () => setAll(false));

  document.getElementById("save-btn").addEventListener("click", () => {
    hideMessage();
    run(async () => {
      await saveRecords();
      await loadSessions();
      showMessage("Attendance saved as a draft. Finalize it when you are ready.", "success");
    });
  });

  document.getElementById("finalize-btn").addEventListener("click", () => {
    hideMessage();
    run(finalizeCurrent);
  });

  document.getElementById("close-btn").addEventListener("click", () => {
    hideMessage();
    current = null;
    document.getElementById("session-panel").hidden = true;
  });
}

// ---------- recent sessions ----------
async function loadSessions() {
  const data = await apiFetch("/faculty/attendance-sessions");
  const body = document.getElementById("sessions-body");
  body.replaceChildren();

  document.getElementById("no-sessions").hidden = data.sessions.length > 0;

  data.sessions.forEach((s) => {
    const badge = document.createElement("span");
    badge.className = "badge " + s.status;
    badge.textContent = s.status;
    const statusCell = document.createElement("td");
    statusCell.append(badge);

    const title = s.subject_code + " - " + s.subject_name + " (Section " + s.section + ")";
    const actions = document.createElement("td");
    actions.append(
      actionButton(s.status === "draft" ? "Resume" : "View", () => {
        hideMessage();
        run(() => openSession(s.id, title));
      })
    );

    const row = document.createElement("tr");
    row.append(
      cell(formatDate(s.session_date)),
      cell(shortTime(s.start_time) + " - " + shortTime(s.end_time)),
      cell(s.subject_code + " - " + s.subject_name),
      cell(s.section),
      statusCell,
      cell(s.present + " / " + s.marked),
      actions
    );
    body.append(row);
  });
}