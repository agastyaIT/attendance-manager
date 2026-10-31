// Pages to open after login. Add faculty and student when those dashboards exist.
const DASHBOARDS = {
  admin: "/app/admin/dashboard.html",
  student: "/app/student/dashboard.html",
  faculty: "/app/faculty/dashboard.html",
};
function errorMessage(data, status) {
  if (data && typeof data.detail === "string") {
    return data.detail;
  }
  if (data && Array.isArray(data.detail)) {
    return data.detail
      .map((item) => item.loc.slice(1).join(".") + ": " + item.msg)
      .join("; ");
  }
  return "Request failed (" + status + ")";
}

// Every call to the backend goes through here.
async function apiFetch(path, options = {}) {
  const token = sessionStorage.getItem("token");
  const headers = {};

  if (options.body) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }

  const response = await fetch(path, { ...options, headers });

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  // A 401 while holding a token means it expired or is invalid.
  if (response.status === 401 && token) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    throw new Error(errorMessage(data, response.status));
  }

  return data;
}

function logout() {
  sessionStorage.clear();
  window.location.href = "/app/index.html";
}

// Convenience for dashboard pages. This is only for user experience;
// the real permission check is always done by the server.
function requireLogin(role) {
  const token = sessionStorage.getItem("token");
  let user = null;

  try {
    user = JSON.parse(sessionStorage.getItem("user"));
  } catch (error) {
    user = null;
  }

  if (!token || !user || user.role !== role) {
    logout();
    return null;
  }
  return user;
}

function goToDashboard(role) {
  const target = DASHBOARDS[role];
  if (target) {
    window.location.href = target;
  } else {
    showMessage("The " + role + " dashboard is not built yet.", "error");
  }
}

// ---------- small UI helpers ----------
function showMessage(text, type) {
  const box = document.getElementById("message");
  if (!box) return;
  box.textContent = text;
  box.className = "msg " + type;
  box.hidden = false;
}

function hideMessage() {
  const box = document.getElementById("message");
  if (box) box.hidden = true;
}

// textContent (not innerHTML) so a name like "<script>" is shown as plain text.
function cell(text) {
  const td = document.createElement("td");
  td.textContent = text === null || text === undefined ? "" : text;
  return td;
}

function actionButton(label, onClick, extraClass) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn small " + (extraClass || "");
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function fillSelect(id, items, valueOf, labelOf) {
  const select = document.getElementById(id);
  const previous = select.value;
  select.replaceChildren();

  items.forEach((item) => {
    const option = document.createElement("option");
    option.value = valueOf(item);
    option.textContent = labelOf(item);
    select.append(option);
  });

  if (previous) select.value = previous;
}

// Helpers used by student.js
function getUser() {
  return JSON.parse(sessionStorage.getItem("user"));
}

// ---------- added for the login, register and student pages ----------
function saveSession(token, user) {
  sessionStorage.setItem("token", token);
  sessionStorage.setItem("user", JSON.stringify(user));
}

function getToken() {
  return sessionStorage.getItem("token");
}

function makeElement(tag, text, className) {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) {
    element.className = className;
  }
  return element;
}

// Works both ways: apiRequest(path, options) and apiRequest(path, "POST", body)
function apiRequest(path, methodOrOptions = {}, body = null) {
  if (typeof methodOrOptions === "string") {
    const options = { method: methodOrOptions };
    if (body) {
      options.body = JSON.stringify(body);
    }
    return apiFetch(path, options);
  }
  return apiFetch(path, methodOrOptions);
}