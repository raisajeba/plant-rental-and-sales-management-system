let currentAdminUserId;

function createSelect(options, selectedValue, label) {
  const select = document.createElement("select");
  select.setAttribute("aria-label", label);

  options.forEach(({ value, text }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    option.selected = value === selectedValue;
    select.append(option);
  });

  return select;
}

async function loadAdminUsers() {
  const body = document.getElementById("adminUsers");
  body.replaceChildren();

  try {
    const [users, roles] = await Promise.all([
      apiRequest("/admin/users", { auth: true }),
      apiRequest("/admin/roles", { auth: true })
    ]);

    if (users.length === 0) {
      const row = body.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 5;
      cell.className = "order-history-state";
      cell.textContent = "No users found.";
      return;
    }

    users.forEach((user) => {
      const row = body.insertRow();
      row.insertCell().textContent = user.name;
      row.insertCell().textContent = user.email;

      const roleCell = row.insertCell();
      const roleSelect = createSelect(
        roles.map((role) => ({
          value: String(role.id),
          text: role.role_name
        })),
        String(user.role.id),
        `Role for ${user.email}`
      );
      roleCell.append(roleSelect);

      const statusCell = row.insertCell();
      const statusSelect = createSelect(
        ["active", "inactive", "blocked"].map((status) => ({
          value: status,
          text: status
        })),
        user.status,
        `Status for ${user.email}`
      );
      statusCell.append(statusSelect);

      const actionCell = row.insertCell();
      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.className = "btn btn-primary";
      saveButton.textContent = "Save";
      saveButton.disabled = user.id === currentAdminUserId;
      saveButton.addEventListener("click", async () => {
        saveButton.disabled = true;
        try {
          await apiRequest(`/admin/users/${user.id}`, {
            method: "PATCH",
            body: {
              role_id: Number(roleSelect.value),
              status: statusSelect.value
            },
            auth: true
          });
          showMessage("User access updated.", "success");
          await loadAdminUsers();
        } catch (error) {
          showMessage(error.message);
          saveButton.disabled = false;
        }
      });
      actionCell.append(saveButton);
    });
  } catch (error) {
    const row = body.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 5;
    cell.className = "order-history-state";
    cell.textContent = error.message;
  }
}

document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.page !== "admin") {
    return;
  }

  try {
    const currentUser = await apiRequest("/users/me", { auth: true });
    currentAdminUserId = currentUser.id;
    await loadAdminUsers();
  } catch (error) {
    showMessage(error.message);
  }
});
