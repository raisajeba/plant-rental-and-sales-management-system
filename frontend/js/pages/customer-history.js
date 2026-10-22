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

function openRentalPayment(order) {
  const dialog = document.getElementById("rentalPaymentDialog");
  document.getElementById("rentalPaymentSummary").textContent =
    `Rental #${order.id} · ${order.items.map((item) => `${item.plant_name} × ${item.quantity}`).join(", ")} · ${formatOrderMoney(order.total_amount)}`;
  document.getElementById("rentalPaymentForm").dataset.orderId = String(order.id);
  dialog.showModal();
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
  const paymentStatus = new URLSearchParams(window.location.search).get("status");
  if (paymentStatus === "success") {
    showMessage("Payment confirmed. Your order is now marked as paid.", "success");
  } else if (paymentStatus === "error") {
    showMessage("Payment could not be confirmed. You can retry checkout from your order.", "error");
  } else if (paymentStatus === "cancelled") {
    showMessage("Payment was cancelled. Your order remains unpaid.", "error");
  }

  const tbody = document.getElementById("orderHistoryBody");
  const emptyState = document.getElementById("orderHistoryEmpty");
  const tableWrap = document.getElementById("orderHistoryTableWrap");
  const paymentDialog = document.getElementById("rentalPaymentDialog");
  const paymentForm = document.getElementById("rentalPaymentForm");
  const paymentButton = document.getElementById("submitRentalPaymentButton");
  try {
    const orders = await apiRequest("/orders/my-orders", { auth: true });
    tbody.replaceChildren();

    if (orders.length === 0) {
      emptyState.hidden = false;
      tableWrap.hidden = true;
      return;
    }

    emptyState.hidden = true;
    tableWrap.hidden = false;
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
      badge.textContent = order.order_type === "Rent" && order.status === "Pending"
        ? "Waiting for Nursery Owner Acceptance"
        : order.status;
      statusCell.append(badge);
      const paymentBadge = document.createElement("span");
      const paymentStatus = order.payment_status || "Pending";
      paymentBadge.className = `badge payment-${paymentStatus.toLowerCase()}`;
      paymentBadge.textContent = `Payment: ${paymentStatus}`;
      statusCell.append(document.createElement("br"), paymentBadge);

      const actionCell = row.insertCell();
      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-reset";
      button.textContent = "View details";
      button.addEventListener("click", () => showOrderDetails(row, order));
      actionCell.append(button);
      if (
        order.order_type === "Rent" &&
        order.status === "Approved" &&
        String(order.payment_status).toUpperCase() !== "PAID"
      ) {
        const payButton = document.createElement("button");
        payButton.type = "button";
        payButton.className = "btn btn-primary";
        payButton.textContent = "Pay Now";
        payButton.addEventListener("click", () => openRentalPayment(order));
        actionCell.append(document.createElement("br"), payButton);
      }
    });
  } catch (error) {
    const errorMessage = error.status
      ? `Request failed (HTTP ${error.status}): ${error.message}`
      : `Request failed: ${error.message}`;
    showMessage(errorMessage);
    emptyState.hidden = true;
    tableWrap.hidden = false;
    tbody.replaceChildren();
    const row = tbody.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 7;
    cell.className = "order-history-state";
    cell.textContent = "Unable to load your order history.";
  }
}

document.getElementById("rentalPaymentForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = document.getElementById("submitRentalPaymentButton");
  const orderId = Number(form.dataset.orderId);
  button.disabled = true;
  try {
    const data = await apiRequest("/payment/initiate", {
      method: "POST",
      auth: true,
      body: {
        order_type: "rental",
        order_id: orderId,
        phone: document.getElementById("rentalPaymentPhone").value.trim(),
        address: document.getElementById("rentalPaymentAddress").value.trim(),
        city: document.getElementById("rentalPaymentCity").value.trim(),
        postcode: document.getElementById("rentalPaymentPostcode").value.trim(),
      },
    });
    window.location.href = data.GatewayPageURL;
  } catch (error) {
    showMessage(error.message);
    button.disabled = false;
  }
});

document.getElementById("closeRentalPaymentButton").addEventListener("click", () => {
  document.getElementById("rentalPaymentDialog").close();
});
document.getElementById("cancelRentalPaymentButton").addEventListener("click", () => {
  document.getElementById("rentalPaymentDialog").close();
});

window.dashboardShell.ready.then(({ user }) => {
  if (user && user.role.role_name === "User") {
    loadCustomerHistory();
  }
});
