/* =========================================================
 PAGE: dashboard
 ========================================================= */
function initDashboardPage() {
 const urlParams = new URLSearchParams(window.location.search);
 const paymentStatus = urlParams.get("status");


 // Jodi payment status URL-e thake, tahole token na thakteo login-e redirect hobe na
 if (!getToken() && !paymentStatus) {
   window.location.replace("login.html");
   return;
 }


 async function loadDashboard() {
   try {
     // Payment status thakle message dekhano
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
       const ordersTableBody = document.querySelector(".content tbody");
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
       // Token ba API error holeo dashboard theke kickout korbe na, shudhu error message dibe
       showMessage(err.message, "error");
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
