/* =========================================================
   PAGE: rent (Rent Plants)
   ========================================================= */
function initRentPage() {
  const grid = document.getElementById("rentPlantsGrid");
  const searchInput = document.getElementById("searchInput");
  const today = new Date().toISOString().slice(0, 10);
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
        : "No plants available for rent right now.";
      grid.appendChild(emptyState);
      return;
    }

    matches.forEach((plant) => {
      const card = document.createElement("div");
      card.className = "card rental-plant-card";

      const image = document.createElement("img");
      image.className = "rental-plant-image";
      image.alt = plant.name;
      image.hidden = !plant.image_url;
      if (plant.image_url) {
        image.src = `${API_ORIGIN}${plant.image_url}`;
      }

      const plantName = document.createElement("h3");
      plantName.textContent = plant.name;
      const category = document.createElement("p");
      category.textContent = `Category: ${plant.category || "General"}`;
      const price = document.createElement("p");
      price.className = "rental-plant-price";
      price.textContent = `৳${Number(plant.rent_price).toFixed(2)} / day`;

      const form = document.createElement("form");
      form.className = "rental-request-form";
      const quantityLabel = document.createElement("label");
      quantityLabel.textContent = "Quantity";
      const quantity = document.createElement("input");
      quantity.type = "number";
      quantity.min = "1";
      quantity.max = String(plant.available_quantity);
      quantity.value = "1";
      quantity.setAttribute("aria-label", `Quantity to rent for ${plant.name}`);
      quantity.required = true;
      quantityLabel.append(quantity);

      const startDateLabel = document.createElement("label");
      startDateLabel.textContent = "Start date";
      const startDate = document.createElement("input");
      startDate.type = "date";
      startDate.min = today;
      startDate.value = today;
      startDate.required = true;
      startDateLabel.append(startDate);

      const endDateLabel = document.createElement("label");
      endDateLabel.textContent = "End date";
      const endDate = document.createElement("input");
      endDate.type = "date";
      endDate.min = today;
      endDate.value = today;
      endDate.required = true;
      endDateLabel.append(endDate);

      const rentButton = document.createElement("button");
      rentButton.type = "submit";
      rentButton.className = "btn btn-primary";
      rentButton.textContent = "Submit rental request";
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const requestedQuantity = Number(quantity.value);
        if (
          !Number.isInteger(requestedQuantity) ||
          requestedQuantity < 1 ||
          requestedQuantity > plant.available_quantity
        ) {
          showMessage(`Choose a quantity between 1 and ${plant.available_quantity}.`);
          return;
        }
        if (!startDate.value || !endDate.value || endDate.value < startDate.value) {
          showMessage("Choose a valid rental start and end date.");
          return;
        }

        rentButton.disabled = true;
        try {
          const rental = await apiRequest("/rentals/requests", {
            method: "POST",
            auth: true,
            body: {
              plant_id: plant.id,
              quantity: requestedQuantity,
              rental_start_date: startDate.value,
              rental_end_date: endDate.value,
            }
          });
          showMessage(
            `Rental request #${rental.rental_id} submitted for ${rental.rental_duration_days} day(s). Total: ৳${Number(rental.total_amount).toFixed(2)}.`,
            "success"
          );
        } catch (error) {
          showMessage(error.message);
        } finally {
          rentButton.disabled = false;
        }
      });

      form.append(quantityLabel, startDateLabel, endDateLabel, rentButton);
      card.append(image, plantName, category, price, form);
      grid.appendChild(card);
    });
  }

  async function loadRentPlants() {
    try {
      availablePlants = await apiRequest("/rentals/plants", { auth: true });
      renderPlants(searchInput.value);
    } catch (err) {
      showMessage(err.message, "error");
      const errorState = document.createElement("p");
      errorState.className = "plant-empty";
      errorState.textContent = `Failed to load rent plants: ${err.message}`;
      grid.replaceChildren(errorState);
    }
  }

  searchInput.addEventListener("input", () => renderPlants(searchInput.value));
  loadRentPlants();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "rent") {
    window.dashboardShell.ready.then(({ user }) => {
      if (user && user.role.role_name === "User") {
        initRentPage();
      }
    });
  }
});