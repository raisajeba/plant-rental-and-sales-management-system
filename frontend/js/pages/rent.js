/* =========================================================
   PAGE: rent (Rent Plants)
   ========================================================= */
function initRentPage() {
  const grid = document.getElementById("rentPlantsGrid");

  async function loadRentPlants() {
    try {
      const plants = await apiRequest("/plants", { auth: true });
      
      if (!plants || plants.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No plants available for rent right now.</p>`;
        return;
      }

      // Filter plants that have rent_price available
      const rentPlants = plants.filter(
        (plant) =>
          plant.rent_price > 0 &&
          plant.available_quantity > 0 &&
          ["available_for_rent", "available_for_both"].includes(
            plant.availability_status
          )
      );

      if (rentPlants.length === 0) {
        grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: #666;">No plants available for rent currently.</p>`;
        return;
      }

      grid.innerHTML = "";
      rentPlants.forEach((plant) => {
        const card = document.createElement("div");
        card.className = "card";
        card.style.cssText = "padding: 1rem; display: flex; flex-direction: column; justify-content: space-between; border-radius: 8px;";

        const plantName = document.createElement("h4");
        plantName.textContent = plant.name;
        const category = document.createElement("p");
        category.textContent = `Category: ${plant.category || "General"}`;
        const price = document.createElement("p");
        price.textContent = `৳${plant.rent_price} / month`;
        const quantity = document.createElement("input");
        quantity.type = "number";
        quantity.min = "1";
        quantity.max = String(plant.available_quantity);
        quantity.value = "1";
        quantity.setAttribute("aria-label", `Quantity to rent for ${plant.name}`);
        const rentButton = document.createElement("button");
        rentButton.type = "button";
        rentButton.className = "btn btn-primary";
        rentButton.textContent = "Rent Now";
        rentButton.addEventListener("click", async () => {
          const months = Number.parseInt(
            document.getElementById("rentalMonths").value,
            10
          );
          const requestedQuantity = Number.parseInt(quantity.value, 10);
          if (!Number.isInteger(months) || months < 1 || months > 120) {
            showMessage("Choose a rental term between 1 and 120 months.");
            return;
          }
          if (
            !Number.isInteger(requestedQuantity) ||
            requestedQuantity < 1 ||
            requestedQuantity > plant.available_quantity
          ) {
            showMessage(`Choose a quantity between 1 and ${plant.available_quantity}.`);
            return;
          }
          rentButton.disabled = true;
          try {
            const order = await apiRequest("/orders/rentals", {
              method: "POST",
              auth: true,
              body: {
                plant_id: plant.id,
                quantity: requestedQuantity,
                rental_months: months
              }
            });
            showMessage(
              `Rental order #${order.id} placed. View it in Purchase History.`,
              "success"
            );
          } catch (error) {
            showMessage(error.message);
          } finally {
            rentButton.disabled = false;
          }
        });

        const details = document.createElement("div");
        details.append(plantName, category, price, quantity, rentButton);
        card.append(details);
        grid.appendChild(card);
      });

    } catch (err) {
      showMessage(err.message, "error");
      grid.innerHTML = `<p style="grid-column: 1/-1; text-align: center; color: red;">Failed to load rent plants.</p>`;
    }
  }

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