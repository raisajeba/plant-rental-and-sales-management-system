const SELL_ORDER_STATUSES = [
  "Pending",
  "Confirmed",
  "Processing",
  "Completed",
  "Cancelled",
];

function appendSellOrderDetails(row, order) {
  const detailsRow = document.createElement("tr");
  detailsRow.className = "order-details-row";
  const detailsCell = document.createElement("td");
  detailsCell.colSpan = 8;

  const list = document.createElement("ul");
  list.className = "order-details-list";
  order.items.forEach((item) => {
    const entry = document.createElement("li");
    entry.textContent =
      `${item.plant_name} — ${item.quantity} × ৳${Number(item.unit_price).toFixed(2)}` +
      ` = ৳${Number(item.total_price).toFixed(2)}`;
    list.append(entry);
  });

  const summary = document.createElement("p");
  summary.textContent =
    `Customer: ${order.customer_name} · Order date: ${formatDate(order.order_date)}`;
  detailsCell.append(summary, list);
  detailsRow.append(detailsCell);
  row.after(detailsRow);
}

function createSellOrderStatusControl(order, refreshOrders) {
  const container = document.createElement("div");
  container.className = "sell-order-status-control";

  const badge = document.createElement("span");
  badge.className = `badge ${order.status.toLowerCase()}`;
  badge.textContent = order.status;

  const select = document.createElement("select");
  select.setAttribute("aria-label", `Update status for order ${order.id}`);
  SELL_ORDER_STATUSES.forEach((status) => {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = status;
    select.append(option);
  });
  select.value = order.status;

  const updateButton = document.createElement("button");
  updateButton.type = "button";
  updateButton.className = "btn btn-reset";
  updateButton.textContent = "Update";
  updateButton.addEventListener("click", async () => {
    updateButton.disabled = true;
    try {
      await apiRequest(`/orders/owner/${order.id}/status`, {
        method: "PATCH",
        body: { status: select.value },
        auth: true,
      });
      showMessage(`Order #GF-${order.id} status updated.`, "success");
      await refreshOrders();
    } catch (error) {
      showMessage(error.message);
    } finally {
      updateButton.disabled = false;
    }
  });

  container.append(badge, select, updateButton);
  return container;
}

function renderSellOrders(tbody, orders, refreshOrders) {
  tbody.replaceChildren();
  if (orders.length === 0) {
    const row = tbody.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 8;
    cell.className = "order-history-state";
    cell.textContent = "No sell orders found.";
    return;
  }

  orders.forEach((order) => {
    const row = tbody.insertRow();
    const plantNames = order.items.map((item) => item.plant_name).join(", ");
    const quantity = order.items.reduce((total, item) => total + item.quantity, 0);
    const values = [
      `#GF-${order.id}`,
      order.customer_name,
      plantNames,
      `${quantity} pcs`,
      `৳${Number(order.total_price).toFixed(2)}`,
      formatDate(order.order_date),
    ];
    values.forEach((value) => {
      row.insertCell().textContent = value;
    });

    const statusCell = row.insertCell();
    statusCell.append(createSellOrderStatusControl(order, refreshOrders));

    const actionCell = row.insertCell();
    const detailsButton = document.createElement("button");
    detailsButton.type = "button";
    detailsButton.className = "btn btn-reset";
    detailsButton.textContent = "View details";
    detailsButton.addEventListener("click", async () => {
      const existingDetails = row.nextElementSibling;
      if (existingDetails?.classList.contains("order-details-row")) {
        existingDetails.remove();
        detailsButton.textContent = "View details";
        return;
      }

      detailsButton.disabled = true;
      try {
        const details = await apiRequest(`/orders/owner/${order.id}`, {
          auth: true,
        });
        appendSellOrderDetails(row, details);
        detailsButton.textContent = "Hide details";
      } catch (error) {
        showMessage(error.message);
      } finally {
        detailsButton.disabled = false;
      }
    });
    actionCell.append(detailsButton);
  });
}

function initSellOrders() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const tbody = document.getElementById("sellOrdersTableBody");

  async function loadSellOrders() {
    try {
      const orders = await apiRequest("/orders/owner", { auth: true });
      renderSellOrders(tbody, orders, loadSellOrders);
    } catch (error) {
      showMessage(error.message);
      tbody.replaceChildren();
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 8;
      cell.className = "order-history-state";
      cell.textContent = "Unable to load sell orders.";
    }
  }

  loadSellOrders();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "sell-orders") {
    initSellOrders();
  }
});
