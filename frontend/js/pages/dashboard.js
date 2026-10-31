/* =========================================================
 PAGE: dashboard
 ========================================================= */
function initDashboardPage() {
    const $ = (id) => document.getElementById(id);
    const urlParams = new URLSearchParams(window.location.search);
    const paymentStatus = urlParams.get("status");

    if (!getToken() && !paymentStatus) {
        window.location.replace("login.html");
        return;
    }

    async function loadDashboard() {
        try {
            if (paymentStatus === "success") {
                if (typeof showMessage === "function") {
                    showMessage("Payment confirmed successfully! Your order is now paid.", "success");
                }
            } else if (paymentStatus === "error" || paymentStatus === "cancelled") {
                if (typeof showMessage === "function") {
                    showMessage("Payment was not completed or cancelled.", "error");
                }
            }

            const data = await apiRequest("/users/me/dashboard", { auth: true });
        
            if (data) {
                console.log("Real dashboard data loaded:", data);

                // 1. Top Stat Cards Update
                const stats = data.stats || {};
                if ($("statOrders")) $("statOrders").textContent = stats.total_orders || 0;
                if ($("statActiveRentals")) $("statActiveRentals").textContent = stats.active_rentals || 0;
                if ($("statMaintenance")) $("statMaintenance").textContent = stats.upcoming_maintenance || 0;
                if ($("statCompletedRentals")) $("statCompletedRentals").textContent = stats.completed_rentals || 0;

                // 2. Recent Orders Table Render (Latest 5 orders)
                const ordersTableBody = document.querySelector(".content tbody") || document.querySelector("table tbody");
                if (ordersTableBody && data.recent_orders) {
                    if (data.recent_orders.length === 0) {
                        ordersTableBody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #666;">No recent orders found.</td></tr>`;
                    } else {
                        ordersTableBody.innerHTML = data.recent_orders.map(order => `
                            <tr style="border-bottom: 1px solid #f2f2f2;">
                                <td style="padding: 0.75rem 0.5rem; font-weight: 600;">#${order.id}</td>
                                <td style="padding: 0.75rem 0.5rem;">${order.plant_name || (order.plant ? order.plant.name : 'Plant')}</td>
                                <td style="padding: 0.75rem 0.5rem;">Buy</td>
                                <td style="padding: 0.75rem 0.5rem;">${order.created_at ? new Date(order.created_at).toLocaleDateString() : '-'}</td>
                                <td style="padding: 0.75rem 0.5rem;">৳${order.total_amount || 0}</td>
                                <td style="padding: 0.75rem 0.5rem;"><span class="badge" style="background: #e6f4ea; color: #137333; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">${order.status}</span></td>
                            </tr>
                        `).join("");
                    }
                }

                // 3. Active Rentals Section Render (Fixed plant name mapping)
                const rentalsContainer = $("activeRentalsGrid");
                if (rentalsContainer && data.active_rentals) {
                    if (data.active_rentals.length === 0) {
                        rentalsContainer.innerHTML = `<p style="color: #666; font-size: 0.9rem;">No active rentals found.</p>`;
                    } else {
                        rentalsContainer.innerHTML = data.active_rentals.map(rental => {
                            const plantName = rental.plant_name || (rental.plant ? rental.plant.name : null) || rental.name || 'Rental Plant';
                            const rentalStatus = rental.status || 'Active';

                            return `
                                <div style="border: 1px solid #eaeaea; border-radius: 8px; padding: 0.75rem; display: flex; gap: 0.75rem; align-items: center;">
                                    <div style="width: 60px; height: 60px; background: #f2f2f2; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem;">🪴</div>
                                    <div>
                                        <strong style="font-size: 0.95rem;">${plantName}</strong>
                                        <p style="margin: 0.2rem 0; font-size: 0.75rem; color: #666;">Active Rental</p>
                                        <span style="background: #e6f4ea; color: #137333; font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 4px;">${rentalStatus}</span>
                                    </div>
                                </div>
                            `;
                        }).join("");
                    }
                }

                // 4. Upcoming Maintenance Render
                const maintenanceList = $("upcomingMaintenanceList");
                if (maintenanceList && data.upcoming_maintenance) {
                    if (maintenanceList && data.upcoming_maintenance.length === 0) {
                        maintenanceList.innerHTML = `<p style="color: #666; font-size: 0.9rem;">No upcoming maintenance tasks.</p>`;
                    } else {
                        maintenanceList.innerHTML = data.upcoming_maintenance.map(item => {
                            const plantName = item.plant_name || 'Plant';
                            const taskType = item.task_type || item.request_type || 'Care Task';
                            const status = item.status || 'Pending';
                            const dueDate = item.due_date || item.preferred_date || 'Soon';

                            return `
                                <div style="padding: 0.75rem; background: #f9f9f9; border-radius: 8px; border-left: 4px solid #1a73e8; margin-bottom: 0.5rem;">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <strong style="font-size: 0.9rem;">${plantName} 💧</strong>
                                        <span style="background: #e8f0fe; color: #1967d2; font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 4px;">${status}</span>
                                    </div>
                                    <p style="margin: 0.3rem 0 0 0; font-size: 0.8rem; color: #666;">💧 ${taskType} · Due: ${dueDate}</p>
                                </div>
                            `;
                        }).join("");
                    }
                }
            }
        } catch (err) {
            console.error("Dashboard Load Error:", err);
            if (typeof showMessage === "function") {
                showMessage(err.message || "Failed to load dashboard data.", "error");
            }
        }
    }

    loadDashboard();
}

document.addEventListener("DOMContentLoaded", () => {
    if (document.body.dataset.page === "dashboard") {
        initDashboardPage();
    }
});