const admin = requireLogin("admin");

if (admin) {
  document.getElementById("whoami").textContent = admin.name;
  document.getElementById("logout-btn").addEventListener("click", logout);
  setupNavigation();
  setupForms();
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
  await loadUsers();
  await loadSubjects();
  await loadAssignments();
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