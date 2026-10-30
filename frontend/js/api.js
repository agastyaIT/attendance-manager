const TOKEN_KEY = "token";
const USER_KEY = "user";

function saveSession(token, user) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function getUser() {
  const text = sessionStorage.getItem(USER_KEY);
  return text ? JSON.parse(text) : null;
}

function requireLogin(role) {
  const user = getUser();
  if (!getToken() || !user || user.role !== role) {
    window.location.href = "/app/";
  }
}

function logout() {
  sessionStorage.clear();
  window.location.href = "/app/";
}

function errorMessage(data) {
  if (typeof data.detail === "string") {
    return data.detail;
  }
  if (Array.isArray(data.detail) && data.detail.length > 0) {
    return data.detail[0].msg;
  }
  return "Something went wrong";
}

async function apiRequest(path, method = "GET", body = null) {
  const headers = {};
  const token = getToken();

  if (token) {
    headers["Authorization"] = "Bearer " + token;
  }

  const options = { method: method, headers: headers };

  if (body) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }

  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));

if (!response.ok) {
    if (response.status === 401 && token) {
      logout();
    }
    throw { status: response.status, message: errorMessage(data) };
  }
  return data;
}