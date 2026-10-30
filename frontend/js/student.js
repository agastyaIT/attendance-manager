requireLogin("student");

const user = getUser();
document.getElementById("user-name").textContent = user.name;
document.getElementById("user-section").textContent = "Section " + user.section;
document.getElementById("logout-btn").addEventListener("click", logout);

async function loadOverall() {
  try {
    const data = await apiRequest("/student/attendance");
    const overall = data.overall;

    const percent = document.getElementById("overall-percent");
    if (overall.percentage === null) {
      percent.textContent = "--";
    } else {
      percent.textContent = overall.percentage + "%";
    }
    percent.className = "big-number " + overall.status;

    document.getElementById("overall-count").textContent =
      "Attended " + overall.attended + " of " + overall.conducted + " classes";
    document.getElementById("overall-message").textContent = overall.message;
  } catch (error) {
    document.getElementById("message").textContent =
      error.message || "Cannot reach the server";
  }
}

loadOverall();