const admin = requireLogin("admin");

if (admin) {
  document.getElementById("whoami").textContent = admin.name;
  document.getElementById("logout-btn").addEventListener("click", logout);
    setupNavigation();
  setupForms();
  setupCorrections();
  run(loadAll);
}


async function run(action) {
  try {
    await action();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadAll() {
  async function loadAll() {
  await loadUsers();
  await loadSubjects();
  await loadAssignments();
  await loadCorrectionFilters();
}
}

function setupNavigation() {
  const buttons = document.querySelectorAll(".nav-btn");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      hideMessage();
      buttons.forEach((b) => b.classList.remove("active"));
      button.classList.add("active");

      document.querySelectorAll(".panel").forEach((panel) => {
        panel.hidden = panel.id !== "section-" + button.dataset.section;
      });

      if (button.dataset.section === "corrections") run(searchSessions);
      if (button.dataset.section === "audit") run(loadAudit);
    });
  });
}

// ---------- users ----------
async function loadUsers() {
  const role = document.getElementById("role-filter").value;
  const data = await apiFetch(role ? "/admin/users?role=" + role : "/admin/users");
  const body = document.getElementById("users-body");
  body.replaceChildren();

  data.users.forEach((u) => {
    const row = document.createElement("tr");
    row.append(cell(u.id), cell(u.name), cell(u.email), cell(u.role), cell(u.section || "-"));

    const actions = document.createElement("td");
    actions.append(actionButton("Edit", () => editUser(u)));
    row.append(actions);

    body.append(row);
  });
}

function editUser(u) {
  const name = prompt("New name:", u.name);
  if (name === null) return;

  const changes = { name: name.trim() };

  if (u.role === "student") {
    const section = prompt("Section (A or B):", u.section);
    if (section === null) return;
    changes.section = section.trim().toUpperCase();
  }

  hideMessage();
  run(async () => {
    await apiFetch("/admin/users/" + u.id, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
    await loadUsers();
    showMessage("User updated", "success");
  });
}

// ---------- subjects ----------
async function loadSubjects() {
  const data = await apiFetch("/admin/subjects");
  const body = document.getElementById("subjects-body");
  body.replaceChildren();

  data.subjects.forEach((s) => {
    const row = document.createElement("tr");
    row.append(cell(s.subject_code), cell(s.subject_name), cell(s.subject_type), cell(s.section || "A and B"));

    const actions = document.createElement("td");
    actions.append(actionButton("Rename", () => renameSubject(s)));
    row.append(actions);

    body.append(row);
  });
}

function renameSubject(s) {
  const name = prompt("New subject name:", s.subject_name);
  if (name === null) return;

  hideMessage();
  run(async () => {
    await apiFetch("/admin/subjects/" + s.id, {
      method: "PATCH",
      body: JSON.stringify({ subject_name: name.trim() }),
    });
    await loadSubjects();
    await loadAssignments();
    showMessage("Subject renamed", "success");
  });
}

// ---------- assignments ----------
async function loadAssignments() {
  const [faculty, subjects, assignments] = await Promise.all([
    apiFetch("/admin/users?role=faculty"),
    apiFetch("/admin/subjects"),
    apiFetch("/admin/assignments"),
  ]);

  fillSelect(
    "assignment-faculty",
    faculty.users,
    (u) => u.id,
    (u) => u.name + " (" + u.email + ")"
  );
  fillSelect(
    "assignment-subject",
    subjects.subjects,
    (s) => s.id,
    (s) => s.subject_code + " - " + s.subject_name
  );

  const body = document.getElementById("assignments-body");
  body.replaceChildren();

  assignments.assignments.forEach((a) => {
    const row = document.createElement("tr");
    row.append(
      cell(a.subject_code + " - " + a.subject_name),
      cell(a.section),
      cell(a.faculty_name)
    );

    const actions = document.createElement("td");
    actions.append(actionButton("Remove", () => removeAssignment(a), "danger"));
    row.append(actions);

    body.append(row);
  });
}

function removeAssignment(a) {
  if (!confirm("Remove this assignment?")) return;

  hideMessage();
  run(async () => {
    await apiFetch("/admin/assignments/" + a.id, { method: "DELETE" });
    await loadAssignments();
    showMessage("Assignment removed", "success");
  });
}

// ---------- forms ----------
function setupForms() {
  document.getElementById("role-filter").addEventListener("change", () => {
    hideMessage();
    run(loadUsers);
  });

  document.getElementById("faculty-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.target;
    hideMessage();

    run(async () => {
      await apiFetch("/admin/faculty", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("faculty-name").value.trim(),
          email: document.getElementById("faculty-email").value.trim(),
          password: document.getElementById("faculty-password").value,
        }),
      });
      form.reset();
      await loadUsers();
      await loadAssignments();
      showMessage("Faculty account created", "success");
    });
  });

  document.getElementById("subject-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.target;
    hideMessage();

    run(async () => {
      const section = document.getElementById("subject-section").value;
      await apiFetch("/admin/subjects", {
        method: "POST",
        body: JSON.stringify({
          subject_code: document.getElementById("subject-code").value.trim(),
          subject_name: document.getElementById("subject-name").value.trim(),
          subject_type: document.getElementById("subject-type").value,
          section: section || null,
        }),
      });
      form.reset();
      await loadSubjects();
      await loadAssignments();
      showMessage("Subject added", "success");
    });
  });

  document.getElementById("assignment-form").addEventListener("submit", (event) => {
    event.preventDefault();
    hideMessage();

    run(async () => {
      await apiFetch("/admin/assignments", {
        method: "POST",
        body: JSON.stringify({
          faculty_id: Number(document.getElementById("assignment-faculty").value),
          subject_id: Number(document.getElementById("assignment-subject").value),
          section: document.getElementById("assignment-section").value,
        }),
      });
      await loadAssignments();
      showMessage("Assignment created", "success");
    });
  });
}

// ---------- corrections and audit log ----------
function formatDate(iso) {
  const parts = iso.split("-");
  return parts[2] + "/" + parts[1] + "/" + parts[0];
}

function shortTime(t) {
  return t.slice(0, 5);
}

// The database stores UTC; show the viewer's local time.
function localTime(utcText) {
  const d = new Date(utcText.replace(" ", "T") + "Z");
  return isNaN(d) ? utcText : d.toLocaleString();
}

function statusBadge(status) {
  const badge = document.createElement("span");
  badge.className = "badge " + status;
  badge.textContent = status;
  const td = document.createElement("td");
  td.append(badge);
  return td;
}

function setupCorrections() {
  document.getElementById("session-filter").addEventListener("submit", (event) => {
    event.preventDefault();
    hideMessage();
    run(searchSessions);
  });
}

async function loadCorrectionFilters() {
  const data = await apiFetch("/admin/subjects");
  fillSelect(
    "filter-subject",
    data.subjects,
    (s) => s.id,
    (s) => s.subject_code + " - " + s.subject_name
  );

  const select = document.getElementById("filter-subject");
  const all = document.createElement("option");
  all.value = "";
  all.textContent = "All subjects";
  select.insertBefore(all, select.firstChild);
  select.value = "";
}

async function searchSessions() {
  const params = [];
  const subject = document.getElementById("filter-subject").value;
  const section = document.getElementById("filter-section").value;
  const day = document.getElementById("filter-date").value;

  if (subject) params.push("subject_id=" + encodeURIComponent(subject));
  if (section) params.push("section=" + encodeURIComponent(section));
  if (day) params.push("session_date=" + encodeURIComponent(day));

  const data = await apiFetch(
    "/admin/attendance-sessions" + (params.length ? "?" + params.join("&") : "")
  );

  document.getElementById("records-panel").hidden = true;
  document.getElementById("no-corr-sessions").hidden = data.sessions.length > 0;

  const body = document.getElementById("corr-sessions-body");
  body.replaceChildren();

  data.sessions.forEach((s) => {
    const title = s.subject_code + " - " + s.subject_name + " (Section " + s.section + ")";
    const actions = document.createElement("td");
    actions.append(
      actionButton("Open", () => {
        hideMessage();
        run(() => openRecords(s.id, title));
      })
    );

    const row = document.createElement("tr");
    row.append(
      cell(formatDate(s.session_date)),
      cell(shortTime(s.start_time) + " - " + shortTime(s.end_time)),
      cell(s.subject_code + " - " + s.subject_name),
      cell(s.section),
      cell(s.faculty_name),
      cell(s.present + " / " + s.marked),
      actions
    );
    body.append(row);
  });
}

async function openRecords(sessionId, title) {
  const data = await apiFetch("/admin/attendance-sessions/" + sessionId + "/records");
  const s = data.session;

  document.getElementById("records-title").textContent =
    title + " | " + formatDate(s.session_date) + " | " +
    shortTime(s.start_time) + " - " + shortTime(s.end_time);

  const body = document.getElementById("records-body");
  body.replaceChildren();

  data.records.forEach((r) => {
    const next = r.status === "present" ? "absent" : "present";
    const actions = document.createElement("td");
    actions.append(
      actionButton("Mark " + next, () => correctRecord(sessionId, r, title, next), "danger")
    );

    const row = document.createElement("tr");
    row.append(cell(r.name), cell(r.email), statusBadge(r.status), actions);
    body.append(row);
  });

  document.getElementById("records-panel").hidden = false;
}

function correctRecord(sessionId, record, title, newStatus) {
  const reason = prompt(
    "Change " + record.name + " from " + record.status + " to " + newStatus +
    ".\n\nReason for the correction (at least 3 characters):"
  );

  if (reason === null) return;

  if (reason.trim().length < 3) {
    showMessage("A reason of at least 3 characters is required", "error");
    return;
  }

  hideMessage();
  run(async () => {
    await apiFetch(
      "/admin/attendance-sessions/" + sessionId + "/records/" + record.student_id,
      { method: "PUT", body: JSON.stringify({ status: newStatus, reason: reason.trim() }) }
    );
    await openRecords(sessionId, title);
    await searchSessionsKeepingRecords(sessionId, title);
    showMessage("Correction saved and recorded in the audit log", "success");
  });
}

// Refresh the session table (so the Present / Marked count updates)
// without closing the student list that is open.
async function searchSessionsKeepingRecords(sessionId, title) {
  await searchSessions();
  await openRecords(sessionId, title);
}

async function loadAudit() {
  const data = await apiFetch("/admin/corrections");
  const body = document.getElementById("audit-body");
  body.replaceChildren();

  document.getElementById("no-audit").hidden = data.corrections.length > 0;

  data.corrections.forEach((c) => {
    const row = document.createElement("tr");
    row.append(
      cell(localTime(c.corrected_at)),
      cell(
        c.subject_code + " | " + formatDate(c.session_date) + " " +
        shortTime(c.start_time) + " | Sec " + c.section
      ),
      cell(c.student_name + " (" + c.student_email + ")"),
      cell(c.old_status + " \u2192 " + c.new_status),
      cell(c.reason),
      cell(c.admin_name)
    );
    body.append(row);
  });
}