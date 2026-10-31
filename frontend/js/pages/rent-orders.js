function initRentOrders() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const tbody = document.getElementById("rentOrdersTableBody");
  const transitions = {
    Approved: ["Active"],
    Confirmed: ["Active"],// changed here
    Active: ["Completed"],
  };

  function addCell(row, value) {
    const cell = row.insertCell();
    cell.style.padding = "1rem";
    cell.textContent = value;
    return cell;
  }

  async function loadRentOrders() {
    try {
      const orders = await apiRequest("/rentals/owner", { auth: true });
      tbody.replaceChildren();
      if (orders.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 8;
        cell.style.textAlign = "center";
        cell.textContent = "No rental orders found.";
        return;
      }

      orders.forEach((order) => {
        const row = tbody.insertRow();
        row.style.borderBottom = "1px solid #f0f0f0";
        addCell(row, `#RENT-${order.id}`);
        addCell(row, order.customer_name);
        addCell(row, order.plant_name);
        addCell(row, String(order.quantity));
        addCell(
          row,
          `${order.rental_start_date} – ${order.rental_end_date} (${order.rental_duration_days} day(s))`
        );
        addCell(row, `৳${Number(order.total_amount).toFixed(2)}`);

        const statusCell = addCell(row, order.status);
        const badge = document.createElement("span");
        badge.className = `badge ${order.status.toLowerCase()}`;
        badge.textContent = order.status;
        statusCell.replaceChildren(badge);

        const actionCell = row.insertCell();
        if (order.status === "Pending") {
          const acceptButton = document.createElement("button");
          acceptButton.type = "button";
          acceptButton.className = "btn btn-primary";
          acceptButton.textContent = "Accept";
          acceptButton.addEventListener("click", () => {
            void updateRentalStatus(order, "Approved", null, acceptButton);
          });
          const rejectButton = document.createElement("button");
          rejectButton.type = "button";
          rejectButton.className = "btn btn-reset";
          rejectButton.textContent = "Reject";
          rejectButton.addEventListener("click", () => {
            const reason = window.prompt("Enter a reason for rejecting this request:");
            if (reason === null) return;
            if (!reason.trim()) {
              showMessage("A rejection reason is required.");
              return;
            }
            void updateRentalStatus(order, "Rejected", reason.trim(), rejectButton);
          });
          actionCell.append(acceptButton, rejectButton);
          return;
        }

        const nextStatuses = [...(transitions[order.status] || [])];
        if (
          ["Approved", "Confirmed"].includes(order.status) &&
          String(order.payment_status).toUpperCase() !== "PAID"
        ) {
          const activeIndex = nextStatuses.indexOf("Active");
          if (activeIndex >= 0) nextStatuses.splice(activeIndex, 1);
        }
        if (nextStatuses.length === 0) {
          actionCell.textContent = "No further actions";
          return;
        }

        const statusSelect = document.createElement("select");
        statusSelect.setAttribute("aria-label", `Update rental ${order.id} status`);
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "Select status";
        statusSelect.append(placeholder);
        nextStatuses.forEach((nextStatus) => {
          const option = document.createElement("option");
          option.value = nextStatus;
          option.textContent = nextStatus;
          statusSelect.append(option);
        });

        const updateButton = document.createElement("button");
        updateButton.type = "button";
        updateButton.className = "btn btn-primary";
        updateButton.textContent = "Update";
        updateButton.addEventListener("click", async () => {
          if (!statusSelect.value) {
            showMessage("Select a valid next status.");
            return;
          }
          await updateRentalStatus(order, statusSelect.value, null, updateButton);
        });
        actionCell.append(statusSelect, updateButton);
      });
    } catch (error) {
      showMessage(error.message, "error");
      tbody.replaceChildren();
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 8;
      cell.style.textAlign = "center";
      cell.textContent = "Failed to load orders.";
    }
  }

  async function updateRentalStatus(order, status, rejectionReason, button) {
    button.disabled = true;
    try {
      const body = { status };
      if (rejectionReason) body.rejection_reason = rejectionReason;
      await apiRequest(`/rentals/owner/${order.id}/status`, {
        method: "PATCH",
        auth: true,
        body,
      });
      showMessage(`Rental #${order.id} updated to ${status}.`, "success");
      await loadRentOrders();
    } catch (error) {
      showMessage(error.message);
      button.disabled = false;
    }
  }

  loadRentOrders();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "rent-orders") {
    initRentOrders();
  }
});
