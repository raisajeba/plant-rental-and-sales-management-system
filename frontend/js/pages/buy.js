/* =========================================================
   PAGE: buy (Buy Plants)
   ========================================================= */
function initBuyPage() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const grid = document.getElementById("buyPlantsGrid");
  const searchInput = document.getElementById("searchInput");
  let availablePlants = [];

  function renderPlants(searchTerm = "") {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const matches = availablePlants.filter((plant) =>
      `${plant.name} ${plant.category || ""}`.toLowerCase().includes(normalizedSearch)
    );

    grid.replaceChildren();
    if (matches.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "plant-empty";
      emptyState.textContent = normalizedSearch
        ? "No plants match your search."
        : "No plants available for purchase right now.";
      grid.appendChild(emptyState);
      return;
    }

    matches.forEach((plant) => {
      const card = document.createElement("div");
      card.className = "card plant-store-card";
      const details = document.createElement("div");
      const image = document.createElement("img");
      image.className = "plant-store-image";
      image.alt = plant.name;
      image.hidden = !plant.image_url;
      const placeholder = document.createElement("div");
      placeholder.className = "plant-store-placeholder";
      placeholder.textContent = plant.image_url ? "" : "🪴";
      if (plant.image_url) {
        image.src = `${API_ORIGIN}${plant.image_url}`;
      }
      image.addEventListener("error", () => {
        image.hidden = true;
        placeholder.style.display = "grid";
        placeholder.textContent = "🪴";
      });
      const name = document.createElement("h3");
      name.textContent = plant.name;
      const category = document.createElement("p");
      category.textContent = `Category: ${plant.category || "General"}`;
      const price = document.createElement("p");
      price.className = "plant-store-price";
      price.textContent = `৳${Number(plant.buy_price).toFixed(2)}`;
      const addButton = document.createElement("button");
      addButton.type = "button";
      addButton.className = "btn btn-primary plant-store-action";
      addButton.textContent = "Add to Cart";
      addButton.addEventListener("click", () => addToCart(plant.id, "buy"));

      details.append(image, placeholder, name, category, price);
      card.append(details, addButton);
      grid.appendChild(card);
    });
  }

  async function loadBuyPlants() {
    try {
      const plants = await apiRequest("/plants", { auth: true });
      availablePlants = plants.filter((plant) =>
        ["available_for_sale", "available_for_both"].includes(plant.availability_status) &&
        plant.available_quantity > 0 &&
        plant.buy_price !== null &&
        Number(plant.buy_price) > 0
      );
      renderPlants(searchInput.value);
    } catch (err) {
      showMessage(err.message, "error");
      const errorState = document.createElement("p");
      errorState.className = "plant-empty";
      errorState.textContent = `Failed to load plants: ${err.message}`;
      grid.replaceChildren(errorState);
    }
  }

  searchInput.addEventListener("input", () => renderPlants(searchInput.value));
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