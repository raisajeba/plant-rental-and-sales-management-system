function initRentOrders() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const tbody = document.getElementById("rentOrdersTableBody");

  async function loadRentOrders() {
    try {
      const orders = await apiRequest("/api/v1/rentals/owner", { auth: true });
      if (!orders || orders.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: #666;">No rental orders found.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      orders.forEach(order => {
        const row = document.createElement("tr");
        row.style.borderBottom = "1px solid #f0f0f0";
        row.innerHTML = `
          <td style="padding: 1rem; font-weight: 600;">#RENT-${order.id}</td>
          <td style="padding: 1rem;">${order.customer_name || 'Customer'}</td>
          <td style="padding: 1rem;">${order.plant_name}</td>
          <td style="padding: 1rem;">${order.quantity}</td>
          <td style="padding: 1rem; color: #666;">${order.rental_period || 'N/A'}</td>
          <td style="padding: 1rem; font-weight: 700; color: #137333;">৳${order.total_amount}</td>
          <td style="padding: 1rem;"><span class="badge ${order.status.toLowerCase()}">${order.status}</span></td>
          <td style="padding: 1rem;"><button onclick="viewOrderDetails(${order.id})" style="background: #f1f3f4; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-weight: 600;">View Details</button></td>
        `;
        tbody.appendChild(row);
      });
    } catch (err) {
      showMessage(err.message, "error");
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 2rem; color: red;">Failed to load orders.</td></tr>`;
    }
  }

  loadRentOrders();
}

window.viewOrderDetails = function(orderId) {
  showMessage(`Opening details for order #${orderId}`, "success");
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "rent-orders") {
    initRentOrders();
  }
});