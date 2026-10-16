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

function formatRegistrationDate(value) {
  return new Date(value).toLocaleString();
}

function appendAccountDetails(row, user) {
  const detailsRow = document.createElement("tr");
  detailsRow.dataset.userDetails = String(user.id);
  const cell = detailsRow.insertCell();
  cell.colSpan = 7;
  cell.className = "order-history-state";
  cell.textContent = [
    `User ID: ${user.id}`,
    `Name: ${user.name}`,
    `Email: ${user.email}`,
    `Role: ${user.role.role_name}`,
    `Status: ${user.status}`,
    `Registered: ${formatRegistrationDate(user.created_at)}`,
    `Last updated: ${formatRegistrationDate(user.updated_at)}`
  ].join(" | ");
  row.after(detailsRow);
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
      cell.colSpan = 7;
      cell.className = "order-history-state";
      cell.textContent = "No users found.";
      return;
    }

    users.forEach((user) => {
      const row = body.insertRow();
      row.insertCell().textContent = user.id;
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
        [
          { value: "active", text: "Active" },
          { value: "inactive", text: "Inactive" },
          { value: "blocked", text: "Blocked" }
        ],
        user.status,
        `Status for ${user.email}`
      );
      statusCell.append(statusSelect);
      row.insertCell().textContent = formatRegistrationDate(user.created_at);

      const actionCell = row.insertCell();
      const detailsButton = document.createElement("button");
      detailsButton.type = "button";
      detailsButton.className = "btn btn-dark";
      detailsButton.textContent = "Details";
      detailsButton.addEventListener("click", async () => {
        const existingDetailsRow = row.nextElementSibling;
        if (
          existingDetailsRow &&
          existingDetailsRow.dataset.userDetails === String(user.id)
        ) {
          existingDetailsRow.remove();
          detailsButton.textContent = "Details";
          return;
        }

        try {
          const account = await apiRequest(`/admin/users/${user.id}`, {
            auth: true
          });
          appendAccountDetails(row, account);
          detailsButton.textContent = "Hide details";
        } catch (error) {
          showMessage(error.message);
        }
      });
      actionCell.append(detailsButton);

      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.className = "btn btn-primary";
      saveButton.textContent = "Save";
      saveButton.disabled = user.id === currentAdminUserId;
      saveButton.style.marginLeft = "8px";
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
    cell.colSpan = 7;
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
