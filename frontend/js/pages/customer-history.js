function formatOrderMoney(amount) {
  return `৳${Number(amount).toFixed(2)}`;
}

function appendOrderDetails(row, order) {
  const detailsRow = document.createElement("tr");
  detailsRow.className = "order-details-row";
  const detailsCell = document.createElement("td");
  detailsCell.colSpan = 7;

  const list = document.createElement("ul");
  list.className = "order-details-list";
  order.items.forEach((item) => {
    const entry = document.createElement("li");
    const rentalTerm = item.rental_months
      ? ` · ${item.rental_months} month${item.rental_months === 1 ? "" : "s"}`
      : "";
    entry.textContent =
      `${item.plant_name} — ${item.quantity} × ${formatOrderMoney(item.unit_price)}` +
      `${rentalTerm} = ${formatOrderMoney(item.total_price)}`;
    list.append(entry);
  });

  detailsCell.append(list);
  detailsRow.append(detailsCell);
  row.after(detailsRow);
}

async function showOrderDetails(row, order) {
  const existingDetails = row.nextElementSibling;
  if (existingDetails?.classList.contains("order-details-row")) {
    existingDetails.remove();
    row.querySelector("button").textContent = "View details";
    return;
  }

  const button = row.querySelector("button");
  button.disabled = true;
  try {
    const orderType = order.order_type.toLowerCase();
    const details = await apiRequest(
      `/orders/my-orders/${orderType}/${order.id}`,
      { auth: true }
    );
    appendOrderDetails(row, details);
    button.textContent = "Hide details";
  } catch (error) {
    showMessage(error.message);
  } finally {
    button.disabled = false;
  }
}

async function loadCustomerHistory() {
  const tbody = document.getElementById("orderHistoryBody");
  try {
    const orders = await apiRequest("/orders/my-orders", { auth: true });
    tbody.replaceChildren();

    if (orders.length === 0) {
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 7;
      cell.className = "order-history-state";
      cell.textContent = "You do not have any purchases or rentals yet.";
      return;
    }

    orders.forEach((order) => {
      const row = tbody.insertRow();
      const plants = order.items
        .map((item) => `${item.plant_name} × ${item.quantity}`)
        .join(", ");
      const statusClass = order.status.toLowerCase().replace(/[^a-z0-9-]/g, "");

      [
        `#${order.id}`,
        order.order_type,
        plants,
        formatOrderMoney(order.total_amount),
        new Date(order.created_at).toLocaleString(),
      ].forEach((value) => {
        row.insertCell().textContent = value;
      });

      const statusCell = row.insertCell();
      const badge = document.createElement("span");
      badge.className = `badge ${statusClass}`;
      badge.textContent = order.status;
      statusCell.append(badge);

      const actionCell = row.insertCell();
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-reset";
      button.textContent = "View details";
      button.addEventListener("click", () => showOrderDetails(row, order));
      actionCell.append(button);
    });
  } catch (error) {
    showMessage(error.message);
    tbody.replaceChildren();
    const row = tbody.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 7;
    cell.className = "order-history-state";
    cell.textContent = "Unable to load your order history.";
  }
}

window.dashboardShell.ready.then(({ user }) => {
  if (user && user.role.role_name === "User") {
    loadCustomerHistory();
  }
});
