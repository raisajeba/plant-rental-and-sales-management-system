/* =========================================================
   PAGE: rent (Rent Plants)
   ========================================================= */
function initRentPage() {
  const grid = document.getElementById("rentPlantsGrid");
  const searchInput = document.getElementById("searchInput");
  const today = new Date().toISOString().slice(0, 10);
  const quickViewDialog = document.getElementById("plantQuickViewDialog");
  const closeQuickViewButton = document.getElementById("closeQuickViewButton");
  const quickViewImage = document.getElementById("quickViewImage");
  const quickViewTitle = document.getElementById("quickViewTitle");
  const quickViewCategory = document.getElementById("quickViewCategory");
  const quickViewNursery = document.getElementById("quickViewNursery");
  const quickViewPrice = document.getElementById("quickViewPrice");
  const quickViewCare = document.getElementById("quickViewCare");
  const quickViewStock = document.getElementById("quickViewStock");
  const quickViewForm = document.getElementById("quickViewRentForm");
  const quickViewQuantity = document.getElementById("quickViewQuantity");
  const quickViewStartDate = document.getElementById("quickViewStartDate");
  const quickViewEndDate = document.getElementById("quickViewEndDate");
  const quickViewAction = document.getElementById("quickViewAction");

  // Review elements inside Quick View Modal
  const reviewsListContainer = quickViewDialog.querySelector(".reviews-list-container");
  const quickViewReviewForm = document.getElementById("quickViewReviewForm");
  const reviewRatingSelect = quickViewReviewForm ? quickViewReviewForm.querySelector(".review-rating-select") : null;
  const reviewCommentInput = quickViewReviewForm ? quickViewReviewForm.querySelector(".review-comment-input") : null;
  const reviewSubmitButton = quickViewReviewForm ? quickViewReviewForm.querySelector("button[type='submit']") : null;

  let availablePlants = [];
  let quickViewPlant = null;

  function getPlantImageUrl(imageUrl, highResolution = false) {
    if (!imageUrl) return "";
    const url = new URL(imageUrl, API_ORIGIN);
    if (highResolution && url.hostname === "images.unsplash.com") {
      url.searchParams.set("w", "1200");
      url.searchParams.set("q", "90");
    }
    return url.href;
  }

  async function fetchAndDisplayReviews(plantId) {
    if (!reviewsListContainer) return;
    reviewsListContainer.replaceChildren();
    const loadingText = document.createElement("p");
    loadingText.className = "no-reviews-text";
    loadingText.textContent = "Loading reviews...";
    reviewsListContainer.append(loadingText);

    try {
      const reviews = await apiRequest(`/reviews/plant/${plantId}`);
      if (!quickViewPlant || quickViewPlant.id !== plantId) return;

      reviewsListContainer.replaceChildren();
      if (!reviews || reviews.length === 0) {
        const emptyText = document.createElement("p");
        emptyText.textContent = "No reviews yet. Be the first to review!";
        emptyText.style.color = "#666";
        reviewsListContainer.append(emptyText);
        return;
      }

      for (const review of reviews) {
        const reviewItem = document.createElement("div");
        reviewItem.style.borderBottom = "1px solid #f0f0f0";
        reviewItem.style.padding = "6px 0";

        const ratingDiv = document.createElement("div");
        ratingDiv.style.fontWeight = "600";
        ratingDiv.style.color = "#2e7d32";
        ratingDiv.textContent = `Rating: ${'★'.repeat(review.rating)}`;

        const commentP = document.createElement("p");
        commentP.style.margin = "2px 0";
        commentP.style.color = "#333";
        commentP.textContent = review.comment;

        reviewItem.append(ratingDiv, commentP);
        reviewsListContainer.append(reviewItem);
      }
    } catch (error) {
      if (!quickViewPlant || quickViewPlant.id !== plantId) return;
      reviewsListContainer.replaceChildren();
      const errorText = document.createElement("p");
      errorText.textContent = "Failed to load reviews.";
      errorText.style.color = "#d9534f";
      reviewsListContainer.append(errorText);
    }
  }

  function openQuickView(plant) {
    quickViewPlant = plant;
    quickViewTitle.textContent = plant.name;
    quickViewCategory.textContent = plant.category || "General";
    quickViewNursery.textContent = `From ${plant.nursery_name || "GreenNest nursery"}`;
    quickViewPrice.textContent = `৳${Number(plant.rent_price).toFixed(2)} / day`;
    quickViewCare.textContent = plant.care_instructions || "Care details are not available yet.";
    quickViewStock.textContent = plant.available_quantity > 0
      ? `${plant.available_quantity} available`
      : "Currently out of stock";
    quickViewImage.hidden = !plant.image_url;
    quickViewImage.alt = `${plant.name} plant`;
    if (plant.image_url) {
      quickViewImage.src = getPlantImageUrl(plant.image_url, true);
    } else {
      quickViewImage.removeAttribute("src");
    }
    quickViewQuantity.max = String(plant.available_quantity);
    quickViewQuantity.value = "1";
    quickViewStartDate.min = today;
    quickViewStartDate.value = today;
    quickViewEndDate.min = today;
    quickViewEndDate.value = today;

    if (reviewCommentInput) reviewCommentInput.value = "";
    if (reviewRatingSelect) reviewRatingSelect.value = "5";

    fetchAndDisplayReviews(plant.id);
    quickViewDialog.showModal();
  }

  if (quickViewReviewForm) {
    quickViewReviewForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (!quickViewPlant) return;

      const rating = Number(reviewRatingSelect.value);
      const comment = reviewCommentInput.value.trim();
      if (!comment) return;

      if (reviewSubmitButton) reviewSubmitButton.disabled = true;
      try {
        await apiRequest("/reviews", {
          method: "POST",
          auth: true,
          body: {
            plant_id: quickViewPlant.id,
            rating: rating,
            comment: comment
          }
        });
        showMessage("Review submitted successfully!", "success");
        reviewCommentInput.value = "";
        await fetchAndDisplayReviews(quickViewPlant.id);
      } catch (error) {
        showMessage(error.message);
      } finally {
        if (reviewSubmitButton) reviewSubmitButton.disabled = false;
      }
    });
  }

  async function submitRentalRequest(plant, quantityInput, startDateInput, endDateInput, button) {
    const requestedQuantity = Number(quantityInput.value);
    if (
      !Number.isInteger(requestedQuantity) ||
      requestedQuantity < 1 ||
      requestedQuantity > plant.available_quantity
    ) {
      showMessage(`Choose a quantity between 1 and ${plant.available_quantity}.`);
      return;
    }
    if (
      !startDateInput.value ||
      !endDateInput.value ||
      startDateInput.value < today ||
      endDateInput.value < startDateInput.value
    ) {
      showMessage("Choose a valid rental start and end date.");
      return;
    }

    hideMessage();

    button.disabled = true;
    try {
      const rental = await apiRequest("/rentals/requests", {
        method: "POST",
        auth: true,
        body: {
          plant_id: plant.id,
          quantity: requestedQuantity,
          rental_start_date: startDateInput.value,
          rental_end_date: endDateInput.value,
        },
      });
      showMessage(
        `Rental request submitted. Waiting for Nursery Owner Acceptance. Request #${rental.order_identifier}.`,
        "success"
      );
      if (quickViewDialog.open) quickViewDialog.close();
    } catch (error) {
      showMessage(error.message);
    } finally {
      button.disabled = false;
    }
  }

  function renderPlants(searchTerm = "") {
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const matches = availablePlants.filter((plant) =>
      `${plant.name} ${plant.category || ""} ${plant.nursery_name || ""}`
        .toLowerCase()
        .includes(normalizedSearch)
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
        image.src = getPlantImageUrl(plant.image_url);
      }

      const plantName = document.createElement("h3");
      plantName.textContent = plant.name;
      const category = document.createElement("p");
      category.textContent = `Category: ${plant.category || "General"}`;
      const nursery = document.createElement("p");
      nursery.className = "landing-plant-nursery";
      nursery.textContent = `From ${plant.nursery_name || "GreenNest nursery"}`;
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
        await submitRentalRequest(plant, quantity, startDate, endDate, rentButton);
      });

      form.append(quantityLabel, startDateLabel, endDateLabel, rentButton);
      const viewDetailsButton = document.createElement("button");
      viewDetailsButton.type = "button";
      viewDetailsButton.className = "btn btn-reset plant-card-details-action";
      viewDetailsButton.textContent = "View Details";
      viewDetailsButton.addEventListener("click", () => openQuickView(plant));
      card.append(image, plantName, category, nursery, price, viewDetailsButton, form);
      grid.appendChild(card);
    });
  }

  async function loadRentPlants() {
    try {
      availablePlants = await apiRequest("/rentals/plants", { auth: true });
      const nurseryNames = new Map();
      const plantIds = new Set(availablePlants.map((plant) => plant.id));
      let skip = 0;
      while (nurseryNames.size < plantIds.size) {
        const page = await apiRequest(`/plants?skip=${skip}&limit=100`, {
          auth: true,
        });
        for (const plant of page) {
          if (plantIds.has(plant.id) && plant.nursery_name) {
            nurseryNames.set(plant.id, plant.nursery_name);
          }
        }
        if (page.length < 100) break;
        skip += page.length;
      }
      if (nurseryNames.size !== plantIds.size) {
        throw new Error("Could not load nursery names for all rental listings.");
      }
      availablePlants = availablePlants.map((plant) => ({
        ...plant,
        nursery_name: nurseryNames.get(plant.id),
      }));
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
  closeQuickViewButton.addEventListener("click", () => quickViewDialog.close());
  quickViewDialog.addEventListener("click", (event) => {
    if (event.target === quickViewDialog) quickViewDialog.close();
  });
  quickViewForm.addEventListener("submit", (event) => {
    event.preventDefault();
    if (quickViewPlant) {
      void submitRentalRequest(
        quickViewPlant,
        quickViewQuantity,
        quickViewStartDate,
        quickViewEndDate,
        quickViewAction
      );
    }
  });
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