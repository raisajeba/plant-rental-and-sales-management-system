function initNurseryDashboard() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  async function loadDashboardStats() {
    try {
      // Backend API endpoints for nursery overview
      const stats = await apiRequest("/api/v1/nursery/stats", { auth: true });
      if (stats) {
        document.getElementById("totalPlantsCount").textContent = stats.total_plants || 0;
        document.getElementById("pendingOrdersCount").textContent = stats.pending_orders || 0;
        document.getElementById("activeRentalsCount").textContent = stats.active_rentals || 0;
        document.getElementById("totalRevenueDisplay").textContent = `৳${stats.total_revenue || 0}`;
      }
    } catch (err) {
      console.error("Failed to load dashboard metrics", err);
    }
  }

  loadDashboardStats();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "nursery-dashboard") {
    initNurseryDashboard();
  }
});