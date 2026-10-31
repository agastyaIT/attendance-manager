requireLogin("student");

const user = getUser();
document.getElementById("user-name").textContent = user.name;
document.getElementById("user-section").textContent = "Section " + user.section;
document.getElementById("logout-btn").addEventListener("click", logout);

function makeElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  return element;
}

function showOverall(overall) {
  const percent = document.getElementById("overall-percent");
  percent.textContent = overall.percentage === null ? "--" : overall.percentage + "%";
  percent.className = "big-number " + overall.status;

  document.getElementById("overall-count").textContent =
    "Attended " + overall.attended + " of " + overall.conducted + " classes";
  document.getElementById("overall-message").textContent = overall.message;
}

function showWarnings(warnings) {
  const box = document.getElementById("warnings");
  box.innerHTML = "";

  for (const warning of warnings) {
    const text = warning.subject_name + ": " + warning.message;
    box.appendChild(makeElement("div", text, "warning " + warning.status));
  }
}

function showSubjects(subjects) {
  const box = document.getElementById("subjects");
  box.innerHTML = "";

  for (const subject of subjects) {
    const card = makeElement("div", "", "card subject-card clickable");

    card.appendChild(makeElement("h3", subject.subject_name));
    card.appendChild(makeElement("p", subject.subject_code, "code"));

    const percentText = subject.percentage === null ? "--" : subject.percentage + "%";
    card.appendChild(makeElement("p", percentText, "big-number " + subject.status));

    const bar = makeElement("div", "", "bar");
    const fill = makeElement("div", "", "bar-fill " + subject.status);
    fill.style.width = (subject.percentage || 0) + "%";
    bar.appendChild(fill);
    card.appendChild(bar);

    card.appendChild(
      makeElement("p", "Attended " + subject.attended + " of " + subject.conducted)
    );
    card.appendChild(makeElement("p", "Can skip: " + subject.can_skip));
    card.appendChild(makeElement("p", "To recover: " + subject.classes_to_recover));
    card.appendChild(makeElement("p", subject.message));

    card.appendChild(makeElement("p", "View history", "hint"));

    const history = makeElement("div", "", "history");
    history.hidden = true;
    history.addEventListener("click", (event) => event.stopPropagation());
    card.appendChild(history);

    card.tabIndex = 0;
    card.addEventListener("click", () => toggleHistory(subject, card, history));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        toggleHistory(subject, card, history);
      }
    });

    box.appendChild(card);
  }
}

function formatDate(iso) {
  const parts = iso.split("-");
  return parts[2] + "/" + parts[1] + "/" + parts[0];
}

function showHistory(panel, history) {
  panel.innerHTML = "";

  if (history.length === 0) {
    panel.appendChild(makeElement("p", "No finalized classes yet."));
    return;
  }

  const table = document.createElement("table");

  const header = document.createElement("tr");
  header.appendChild(makeElement("th", "Date"));
  header.appendChild(makeElement("th", "Time"));
  header.appendChild(makeElement("th", "Status"));
  table.appendChild(header);

  for (const item of history) {
    const row = document.createElement("tr");
    row.appendChild(makeElement("td", formatDate(item.session_date)));
    row.appendChild(
      makeElement("td", item.start_time.slice(0, 5) + " - " + item.end_time.slice(0, 5))
    );

    const statusCell = document.createElement("td");
    statusCell.appendChild(makeElement("span", item.status, "badge " + item.status));
    row.appendChild(statusCell);

    table.appendChild(row);
  }

  panel.appendChild(table);
}

async function toggleHistory(subject, card, panel) {
  const hint = card.querySelector(".hint");

  if (!panel.hidden) {
    panel.hidden = true;
    hint.textContent = "View history";
    return;
  }

  panel.hidden = false;
  hint.textContent = "Hide history";

  if (panel.dataset.loaded) {
    return;
  }

  panel.textContent = "Loading...";

  try {
    const data = await apiRequest("/student/attendance/" + subject.subject_id);
    showHistory(panel, data.history);
    panel.dataset.loaded = "yes";
  } catch (error) {
    panel.hidden = true;
    hint.textContent = "View history";
    document.getElementById("message").textContent =
      error.message || "Cannot reach the server";
  }
}

async function loadAttendance() {
  try {
    const data = await apiRequest("/student/attendance");
    showOverall(data.overall);
    showWarnings(data.warnings);
    showSubjects(data.subjects);
  } catch (error) {
    document.getElementById("message").textContent =
      error.message || "Cannot reach the server";
  }
}

loadAttendance();


