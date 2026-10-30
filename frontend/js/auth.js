const form = document.getElementById("login-form");
const messageBox = document.getElementById("message");

const HOME_PAGES = {
  student: "/app/student/dashboard.html",
  faculty: "/app/faculty/dashboard.html",
  admin: "/app/admin/dashboard.html",
};

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  messageBox.textContent = "";

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  try {
    const data = await apiRequest("/login", "POST", { email, password });
    saveSession(data.access_token, data.user);
    window.location.href = HOME_PAGES[data.user.role];
  } catch (error) {
    messageBox.textContent = error.message || "Cannot reach the server";
  }
});