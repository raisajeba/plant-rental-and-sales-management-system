/* =========================================================
   PAGE: rent (Rent Plants)
   ========================================================= */
function initRentPage() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const grid = document.getElementById("rentPlantsGrid");

  async function loadRentPlants() {
    try {
      const plants = await apiRequest("/api/v1/plants", { auth: true });
      
      if (!plants || plants.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No plants available for rent right now.</p>`;
        return;
      }

      // Filter plants that have rent_price available
      const rentPlants = plants.filter(p => p.rent_price && p.rent_price > 0);

      if (rentPlants.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No plants available for rent currently.</p>`;
        return;
      }

      grid.innerHTML = "";
      rentPlants.forEach(plant => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.cssText = "padding: 1rem; display: flex; flex-direction: column; justify-content: space-between; border-radius: 8px;";
        
        card.innerHTML = `
          <div>
            <div style="height: 140px; background: #e6f4ea; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 3rem; margin-bottom: 1rem;">🪴</div>
            <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">${plant.name}</h4>
            <p style="margin: 0 0 0.5rem 0; color: #666; font-size: 0.85rem;">Category: ${plant.category || 'General'}</p>
            <p style="margin: 0 0 1rem 0; font-weight: 700; color: #137333; font-size: 1.1rem;">৳${plant.rent_price} / month</p>
          </div>
          <button onclick="addToRentCart(${plant.id})" style="background: #0d3b1e; color: #fff; border: none; padding: 0.5rem; border-radius: 6px; font-weight: 600; cursor: pointer; width: 100%;">Rent Now</button>
        `;
        grid.appendChild(card);
      });

    } catch (err) {
      showMessage(err.message, "error");
      grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: red;">Failed to load rent plants.</p>`;
    }
  }

  loadRentPlants();
}

window.addToRentCart = function(plantId) {
  showMessage(`Plant #${plantId} added to cart for rent!`, "success");
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "rent") {
    initRentPage();
  }
});