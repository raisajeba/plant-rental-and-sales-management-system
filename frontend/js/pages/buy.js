/* =========================================================
   PAGE: buy (Buy Plants)
   ========================================================= */
function initBuyPage() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const grid = document.getElementById("buyPlantsGrid");

  async function loadBuyPlants() {
    try {
      // Backend API theke plants fetch kora
      const plants = await apiRequest("/api/v1/plants", { auth: true });
      
      if (!plants || plants.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No plants available for purchase right now.</p>`;
        return;
      }

      grid.innerHTML = "";
      plants.forEach(plant => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.cssText = "padding: 1rem; display: flex; flex-direction: column; justify-content: space-between; border-radius: 8px;";
        
        card.innerHTML = `
          <div>
            <div style="height: 140px; background: #e6f4ea; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 3rem; margin-bottom: 1rem;">🪴</div>
            <h4 style="margin: 0 0 0.5rem 0; font-size: 1.1rem;">${plant.name}</h4>
            <p style="margin: 0 0 0.5rem 0; color: #666; font-size: 0.85rem;">Category: ${plant.category || 'General'}</p>
            <p style="margin: 0 0 1rem 0; font-weight: 700; color: #137333; font-size: 1.1rem;">৳${plant.buy_price || 'N/A'}</p>
          </div>
          <button onclick="addToCart(${plant.id}, 'buy')" style="background: #0d3b1e; color: #fff; border: none; padding: 0.5rem; border-radius: 6px; font-weight: 600; cursor: pointer; width: 100%;">Add to Cart</button>
        `;
        grid.appendChild(card);
      });

    } catch (err) {
      showMessage(err.message, "error");
      grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: red;">Failed to load plants.</p>`;
    }
  }

  loadBuyPlants();
}

// Global cart action helper
window.addToCart = function(plantId, type) {
  showMessage(`Plant #${plantId} added to cart for ${type}!`, "success");
  // Ekhane cart API call ba local cart state update er logic add kora jabe
};

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "buy") {
    initBuyPage();
  }
});