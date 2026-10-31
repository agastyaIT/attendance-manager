const user = getUser();

if (!sessionStorage.getItem("token") || !user) {
  logout();
} else {
  document.getElementById("who").textContent = user.name + " (" + user.role + ")";

  document.getElementById("back-link").addEventListener("click", (event) => {
    event.preventDefault();
    goToDashboard(user.role);
  });

  const form = document.getElementById("password-form");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const current = document.getElementById("current-password").value;
    const newPassword = document.getElementById("new-password").value;
    const confirm = document.getElementById("confirm-password").value;

    if (newPassword.length < 8) {
      showMessage("New password must be at least 8 characters", "error");
      return;
    }

    if (newPassword !== confirm) {
      showMessage("New passwords do not match", "error");
      return;
    }

    try {
      await apiFetch("/me/password", {
        method: "POST",
        body: JSON.stringify({
          current_password: current,
          new_password: newPassword,
        }),
      });
      form.reset();
      showMessage("Password changed. Use the new one next time you log in.", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
}