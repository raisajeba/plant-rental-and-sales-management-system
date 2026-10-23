/* =========================================================
   PAGE: dashboard
   ========================================================= */
function initDashboardPage() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  async function loadDashboard() {
    try {
      const data = await apiRequest("/users/me/dashboard", { auth: true });
      
      if (data) {
        console.log("Real dashboard data loaded:", data);

        // 1. Stats count update kora (HTML-er stat cards-er ID thakle ekhane basbe)
        // Jemon: document.getElementById("statOrders").textContent = data.stats.total_orders;

        // 2. Recent Orders render kora
        const ordersTableBody = document.querySelector(".content tbody"); // ba sothik table body selector
        if (ordersTableBody && data.recent_orders) {
          if (data.recent_orders.length === 0) {
            ordersTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #666;">No recent orders found.</td></tr>`;
          } else {
            ordersTableBody.innerHTML = data.recent_orders.map(order => `
              <tr style="border-bottom: 1px solid #f2f2f2;">
                <td style="padding: 0.75rem 0.5rem; font-weight: 600;">#${order.id}</td>
                <td style="padding: 0.75rem 0.5rem;">${order.plant_name || 'Plant'}</td>
                <td style="padding: 0.75rem 0.5rem;">Buy</td>
                <td style="padding: 0.75rem 0.5rem;">${new Date(order.created_at).toLocaleDateString()}</td>
                <td style="padding: 0.75rem 0.5rem;">৳${order.total_amount || 0}</td>
                <td style="padding: 0.75rem 0.5rem;"><span class="badge" style="background: #e6f4ea; color: #137333; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${order.status}</span></td>
              </tr>
            `).join("");
          }
        }
      }
    } catch (err) {
      if (typeof showMessage === "function") {
        showMessage(err.message, "error");
      }
    }
  }

  // Function-ti ekhane call korte hobe jate page load holei data fetch hoy
  loadDashboard();
}


document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "dashboard") {
    initDashboardPage();
  }
});