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
    const card = makeElement("div", "", "card subject-card");

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

    box.appendChild(card);
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