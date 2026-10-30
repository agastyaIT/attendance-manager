const form = document.getElementById("register-form");
const messageBox = document.getElementById("message");

function showMessage(text, type) {
  messageBox.textContent = text;
  messageBox.className = type;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage("", "error");

  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const confirm = document.getElementById("confirm").value;
  const section = document.getElementById("section").value;

  if (password.length < 8) {
    showMessage("Password must be at least 8 characters", "error");
    return;
  }

  if (password !== confirm) {
    showMessage("Passwords do not match", "error");
    return;
  }

  try {
    await apiRequest("/register", "POST", { name, email, password, section });
    showMessage("Registered successfully. Redirecting to login...", "success");
    setTimeout(() => {
      window.location.href = "index.html";
    }, 1500);
  } catch (error) {
    showMessage(error.message || "Cannot reach the server", "error");
  }
});