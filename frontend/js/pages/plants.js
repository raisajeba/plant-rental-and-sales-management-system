(function () {
  "use strict";

  const form = document.getElementById("plantFilters");
  const results = document.getElementById("plantResults");
  const summary = document.getElementById("resultSummary");
  const cartItems = document.getElementById("cartItems");
  const cartSummary = document.getElementById("cartSummary");
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

      const cartForm = document.createElement("form");
      cartForm.className = "plant-cart-form";
      const quantityGroup = document.createElement("div");
      quantityGroup.className = "form-group";
      const quantityLabel = document.createElement("label");
      quantityLabel.textContent = "Quantity";
      quantityLabel.htmlFor = `cart-quantity-${plant.id}`;
      const quantityInput = document.createElement("input");
      quantityInput.id = `cart-quantity-${plant.id}`;
      quantityInput.type = "number";
      quantityInput.min = "1";
      quantityInput.max = String(Math.max(plant.available_quantity, 1));
      quantityInput.value = "1";
      quantityInput.required = true;
      quantityGroup.append(quantityLabel, quantityInput);

      const addButton = document.createElement("button");
      addButton.className = "btn btn-primary";
      addButton.type = "submit";
      const canBuy = (
        plant.availability_status === "available_for_sale" ||
        plant.availability_status === "available_for_both"
      ) && plant.available_quantity > 0 && plant.buy_price !== null;
      addButton.textContent = canBuy ? "Add to cart" : "Not available for sale";
      addButton.disabled = !canBuy;

      cartForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        addButton.disabled = true;
        try {
          await apiRequest("/cart/items", {
            method: "POST",
            body: {
              plant_id: plant.id,
              quantity: Number(quantityInput.value),
            },
            auth: true,
          });
          showMessage(`${plant.name} added to your cart.`, "success");
          await loadCart();
        } catch (error) {
          showMessage(error.message);
        } finally {
          addButton.disabled = !canBuy;
        }
      });

      cartForm.append(quantityGroup, addButton);
      card.append(cartForm);

      // --- Review Button & Form Section ---
      // --- Review Button & Form Section ---
      const reviewButton = document.createElement("button");
      reviewButton.className = "btn btn-reset";
      reviewButton.type = "button";
      reviewButton.textContent = "💬 Reviews & Ratings";
      reviewButton.style.marginTop = "10px";

      const reviewContainer = document.createElement("div");
      reviewContainer.className = "plant-review-box hidden";
      reviewContainer.style.marginTop = "8px";
      reviewContainer.style.paddingTop = "8px";
      reviewContainer.style.borderTop = "1px solid #eee";

      reviewContainer.innerHTML = `
        <div class="reviews-list-container" style="max-height: 150px; overflow-y: auto; margin-bottom: 8px; font-size: 13px; color: #555;">
          <p class="no-reviews-text">Loading reviews...</p>
        </div>
        <form class="inline-review-form">
          <select class="review-rating-select" style="padding: 3px; font-size: 12px; margin-bottom: 5px;">
            <option value="5">⭐⭐⭐⭐⭐ (5)</option>
            <option value="4">⭐⭐⭐⭐ (4)</option>
            <option value="3">⭐⭐⭐ (3)</option>
            <option value="2">⭐⭐ (2)</option>
            <option value="1">⭐ (1)</option>
          </select>
          <input type="text" class="review-comment-input" placeholder="Write a review..." style="width: 100%; padding: 5px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 5px;" required />
          <button type="submit" class="btn btn-primary" style="padding: 3px 8px; font-size: 11px;">Submit Review</button>
        </form>
      `;

      const reviewsListContainer = reviewContainer.querySelector(".reviews-list-container");

      // Function to fetch and display reviews
      async function fetchAndDisplayReviews() {
        try {
          const reviews = await apiRequest(`/reviews/plant/${plant.id}`);
          reviewsListContainer.replaceChildren();

          if (reviews.length === 0) {
            const emptyText = document.createElement("p");
            emptyText.textContent = "No reviews yet. Be the first to review!";
            emptyText.style.color = "#666";
            reviewsListContainer.append(emptyText);
            return;
          }

          for (const review of reviews) {
            const reviewItem = document.createElement("div");
            reviewItem.style.borderBottom = "1px solid #f0f0f0";
            reviewItem.style.padding = "4px 0";
            reviewItem.innerHTML = `
              <div style="font-weight: 600; color: #2e7d32;">Rating: ${'⭐'.repeat(review.rating)}</div>
              <p style="margin: 2px 0; color: #333;">${review.comment}</p>
            `;
            reviewsListContainer.append(reviewItem);
          }
        } catch (error) {
          reviewsListContainer.textContent = "Failed to load reviews.";
        }
      }

      // Toggle review box & load reviews on click
      reviewButton.addEventListener("click", () => {
        const isHidden = reviewContainer.classList.toggle("hidden");
        if (!isHidden) {
          fetchAndDisplayReviews();
        }
      });

      // Submit new review
      reviewContainer.querySelector("form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const rating = reviewContainer.querySelector(".review-rating-select").value;
        const comment = reviewContainer.querySelector(".review-comment-input").value;
        
        try {
          await apiRequest("/reviews", {
            method: "POST",
            auth: true,
            body: {
              plant_id: plant.id,
              rating: Number(rating),
              comment: comment
            }
          });
          showMessage("Review submitted successfully!", "success");
          reviewContainer.querySelector(".review-comment-input").value = "";
          await fetchAndDisplayReviews(); // Refresh review list
        } catch (error) {
          showMessage(error.message);
        }
      });

      card.append(reviewButton, reviewContainer);
      // ------------------------------------

      results.append(card);
    }
  }

  function renderCart(items) {
    cartItems.replaceChildren();
    const totalQuantity = items.reduce((total, item) => total + item.quantity, 0);
    cartSummary.textContent = `${totalQuantity} item${totalQuantity === 1 ? "" : "s"}`;
    const totalAmount = items.reduce(
      (total, item) => total + Number(item.total_amount),
      0
    );
    const total = document.createElement("p");
    total.className = "plant-cart-total";
    total.textContent = `Cart total: ${totalAmount.toFixed(2)}`;

    if (items.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "plant-empty";
      emptyState.textContent = "Your cart is empty.";
      cartItems.append(emptyState, total);
      return;
    }

    for (const item of items) {
      const card = document.createElement("article");
      card.className = "card plant-result-card";
      const name = document.createElement("h3");
      name.textContent = item.plant.name;
      const quantity = document.createElement("p");
      quantity.textContent = `Quantity: ${item.quantity}`;
      const price = document.createElement("p");
      price.textContent = `Unit sale price: ${Number(item.plant.buy_price).toFixed(2)}`;
      const lineTotal = document.createElement("p");
      lineTotal.textContent = `Item total: ${Number(item.total_amount).toFixed(2)}`;

      const quantityControls = document.createElement("div");
      quantityControls.className = "plant-cart-form";
      for (const [label, nextQuantity] of [
        ["Decrease quantity", item.quantity - 1],
        ["Increase quantity", item.quantity + 1],
      ]) {
        const button = document.createElement("button");
        button.className = "btn btn-reset";
        button.type = "button";
        button.textContent = label === "Decrease quantity" ? "−" : "+";
        button.setAttribute("aria-label", label);
        button.disabled = nextQuantity < 1 || nextQuantity > item.plant.available_quantity;
        button.addEventListener("click", async () => {
          button.disabled = true;
          try {
            await apiRequest(`/cart/items/${item.id}`, {
              method: "PATCH",
              body: { quantity: nextQuantity },
              auth: true,
            });
            await loadCart();
          } catch (error) {
            showMessage(error.message);
            button.disabled = false;
          }
        });
        quantityControls.append(button);
      }

      const removeButton = document.createElement("button");
      removeButton.className = "btn btn-reset";
      removeButton.type = "button";
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", async () => {
        removeButton.disabled = true;
        try {
          await apiRequest(`/cart/items/${item.id}`, {
            method: "DELETE",
            auth: true,
          });
          showMessage(`${item.plant.name} removed from your cart.`, "success");
          await loadCart();
        } catch (error) {
          showMessage(error.message);
          removeButton.disabled = false;
        }
      });

      card.append(name, quantity, price, lineTotal, quantityControls, removeButton);
      cartItems.append(card);
    }

    cartItems.append(total);
  }

  async function loadCart() {
    try {
      renderCart(await apiRequest("/cart/items", { auth: true }));
    } catch (error) {
      cartItems.replaceChildren();
      cartSummary.textContent = "";
      showMessage(error.message);
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
  loadCart();
})();
