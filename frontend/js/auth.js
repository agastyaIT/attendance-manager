const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    // Forget any old session so a stale token is never sent with the login request.
    sessionStorage.clear();

    try {
      const data = await apiFetch("/login", {
        method: "POST",
        body: JSON.stringify({
          email: document.getElementById("email").value.trim(),
          password: document.getElementById("password").value,
        }),
      });

      sessionStorage.setItem("token", data.access_token);
      sessionStorage.setItem("user", JSON.stringify(data.user));
      goToDashboard(data.user.role);
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
}

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const password = document.getElementById("password").value;
    if (password !== document.getElementById("confirm").value) {
      showMessage("Passwords do not match", "error");
      return;
    }

    try {
      await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify({
          name: document.getElementById("name").value.trim(),
          email: document.getElementById("email").value.trim(),
          password: password,
          section: document.getElementById("section").value,
        }),
      });

      showMessage("Account created. Redirecting to login...", "success");
      setTimeout(() => {
        window.location.href = "/app/index.html";
      }, 1500);
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
}