(function () {
  "use strict";

  const form = document.getElementById("plantFilters");
  const results = document.getElementById("plantResults");
  const summary = document.getElementById("resultSummary");
  const previousButton = document.getElementById("previousPage");
  const nextButton = document.getElementById("nextPage");
  const pageSize = 20;
  let offset = 0;
  let hasNextPage = false;

  function renderPlants(plants) {
    results.replaceChildren();

    if (plants.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "plant-empty";
      emptyState.textContent = "No plants match these filters. Try changing or clearing them.";
      results.append(emptyState);
      return;
    }

    for (const plant of plants) {
      const card = document.createElement("article");
      card.className = "card plant-result-card";

      const name = document.createElement("h3");
      name.textContent = plant.name;

      const category = document.createElement("p");
      category.textContent = `Category: ${plant.category}`;

      const size = document.createElement("p");
      size.textContent = `Size: ${plant.size || "Not specified"}`;

      const nursery = document.createElement("p");
      nursery.textContent = `Nursery: ${plant.nursery_name}`;

      const prices = document.createElement("p");
      const priceParts = [];
      if (plant.buy_price !== null) priceParts.push(`Sale: ${plant.buy_price}`);
      if (plant.rent_price !== null) priceParts.push(`Rent: ${plant.rent_price}`);
      prices.textContent = priceParts.length
        ? priceParts.join(" · ")
        : "Price not specified";

      const stock = document.createElement("p");
      stock.textContent = `Quantity: ${plant.available_quantity}`;

      const availability = document.createElement("span");
      availability.className = "badge";
      availability.textContent = plant.availability_status.replaceAll("_", " ");

      card.append(name, category, size, nursery, prices, stock, availability);
      results.append(card);
    }
  }

  async function loadPlants() {
    hideMessage();
    results.replaceChildren();
    const loading = document.createElement("p");
    loading.textContent = "Loading plants...";
    results.append(loading);
    previousButton.disabled = true;
    nextButton.disabled = true;

    const params = new URLSearchParams();
    for (const [key, value] of new FormData(form)) {
      if (typeof value === "string" && value.trim()) {
        params.set(key, value.trim());
      }
    }
    params.set("skip", String(offset));
    params.set("limit", String(pageSize + 1));

    try {
      const plants = await apiRequest(`/plants?${params.toString()}`, { auth: true });
      hasNextPage = plants.length > pageSize;
      renderPlants(plants.slice(0, pageSize));
      const shownCount = Math.min(plants.length, pageSize);
      summary.textContent = shownCount
        ? `Showing ${offset + 1}–${offset + shownCount} plants`
        : "Showing 0 plants";
      previousButton.disabled = offset === 0;
      nextButton.disabled = !hasNextPage;
    } catch (error) {
      results.replaceChildren();
      showMessage(error.message);
      summary.textContent = "";
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    offset = 0;
    loadPlants();
  });

  form.addEventListener("reset", () => {
    offset = 0;
    window.setTimeout(loadPlants, 0);
  });

  previousButton.addEventListener("click", () => {
    if (offset >= pageSize) {
      offset -= pageSize;
      loadPlants();
    }
  });

  nextButton.addEventListener("click", () => {
    if (hasNextPage) {
      offset += pageSize;
      loadPlants();
    }
  });

  loadPlants();
})();
