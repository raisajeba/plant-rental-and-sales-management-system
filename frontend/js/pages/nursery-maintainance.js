function initNurseryMaintenance() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const tbody = document.getElementById("nurseryMaintenanceTableBody");

  async function loadServiceRequests() {
    try {
      // Backend API for nursery-side service/maintenance requests
      const requests = await apiRequest("/api/v1/nursery/maintenance-requests", { auth: true });
      
      if (!requests || requests.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: #666;">No maintenance service requests found.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      requests.forEach(req => {
        const row = document.createElement("tr");
        row.style.borderBottom = "1px solid #f0f0f0";
        row.innerHTML = `
          <td style="padding: 1rem; font-weight: 600;">#SRV-${req.id}</td>
          <td style="padding: 1rem;">${req.customer_name || 'Customer'}</td>
          <td style="padding: 1rem;">${req.plant_name}</td>
          <td style="padding: 1rem; color: #555;">${req.service_type || 'General Care'}</td>
          <td style="padding: 1rem; color: #666;">${req.scheduled_date || 'Pending'}</td>
          <td style="padding: 1rem;"><span class="badge ${req.status.toLowerCase()}">${req.status}</span></td>
          <td style="padding: 1rem;">
            <button onclick="updateServiceStatus(${req.id}, 'Completed')" style="background: #137333; color: #fff; border: none; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 0.85rem;">Mark Completed</button>
          </td>
        `;
        tbody.appendChild(row);
      });
    } catch (err) {
      showMessage(err.message, "error");
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 2rem; color: red;">Failed to load service requests.</td></tr>`;
    }
  }

  loadServiceRequests();
}

window.updateServiceStatus = function(requestId, status) {
  showMessage(`Maintenance request #SRV-${requestId} updated to ${status}!`, "success");
  // Ekhane API call diye backend-e status update korar logic thakbe
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "nursery-maintenance") {
    initNurseryMaintenance();
  }
});