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
      // Future-ready: API theke user-specific stats, orders, rentals fetch korar endpoint call
      // const data = await apiRequest("/api/v1/users/me/dashboard", { auth: true });
      
      console.log("Dashboard data initialized successfully!");
    } catch (err) {
      showMessage(err.message, "error");
    }
  }

  loadDashboard();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "dashboard") {
    initDashboardPage();
  }
});