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
  const openCartButton = document.getElementById("openCartButton");
  const closeCartButton = document.getElementById("closeCartButton");
  const cartDialog = document.getElementById("buyCartDialog");
  const cartItems = document.getElementById("cartItems");
  const cartSummary = document.getElementById("buyCartSummary");
  const cartSubtotal = document.getElementById("cartSubtotal");
  const cartTotal = document.getElementById("cartTotal");
  const cartItemCount = document.getElementById("cartItemCount");
  const cartFeedback = document.getElementById("cartFeedback");
  const checkoutButton = document.getElementById("checkoutButton");
  const checkoutFields = {
    phone: document.getElementById("checkoutPhone"),
    address: document.getElementById("checkoutAddress"),
    city: document.getElementById("checkoutCity"),
    postcode: document.getElementById("checkoutPostcode"),
  };
  const quickViewDialog = document.getElementById("plantQuickViewDialog");
  const closeQuickViewButton = document.getElementById("closeQuickViewButton");
  const quickViewImage = document.getElementById("quickViewImage");
  const quickViewTitle = document.getElementById("quickViewTitle");
  const quickViewCategory = document.getElementById("quickViewCategory");
  const quickViewNursery = document.getElementById("quickViewNursery");
  const quickViewPrice = document.getElementById("quickViewPrice");
  const quickViewCare = document.getElementById("quickViewCare");
  const quickViewStock = document.getElementById("quickViewStock");
  const quickViewAction = document.getElementById("quickViewAction");
  let availablePlants = [];
  let quickViewPlant = null;
  let currentCartItems = [];

  function setCartFeedback(text, type = "error") {
    cartFeedback.textContent = text;
    cartFeedback.classList.toggle("success", type === "success");
    cartFeedback.hidden = !text;
  }

  function formatPrice(amount) {
    return `৳${Number(amount).toFixed(2)}`;
  }

  function getPlantImageUrl(imageUrl, highResolution = false) {
    if (!imageUrl) return "";
    const url = new URL(imageUrl, API_ORIGIN);
    if (highResolution && url.hostname === "images.unsplash.com") {
      url.searchParams.set("w", "1200");
      url.searchParams.set("q", "90");
    }
    return url.href;
  }

  async function addPlantToCart(plant, button) {
    button.disabled = true;
    try {
      await apiRequest("/cart/items", {
        method: "POST",
        body: { plant_id: plant.id, quantity: 1 },
        auth: true,
      });
      showMessage(`${plant.name} added to your cart.`, "success");
      await loadCart();
    } catch (error) {
      showMessage(error.message);
    } finally {
      button.disabled = false;
    }
  }

  function openQuickView(plant) {
    quickViewPlant = plant;
    quickViewTitle.textContent = plant.name;
    quickViewCategory.textContent = plant.category || "General";
    quickViewNursery.textContent = `From ${plant.nursery_name || "GreenNest nursery"}`;
    quickViewPrice.textContent = formatPrice(plant.buy_price);
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
    quickViewAction.disabled = plant.available_quantity < 1;
    quickViewDialog.showModal();
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
        image.src = getPlantImageUrl(plant.image_url);
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
      const nursery = document.createElement("p");
      nursery.className = "landing-plant-nursery";
      nursery.textContent = `From ${plant.nursery_name || "GreenNest nursery"}`;
      const price = document.createElement("p");
      price.className = "plant-store-price";
      price.textContent = formatPrice(plant.buy_price);
      const addButton = document.createElement("button");
      addButton.type = "button";
      addButton.className = "btn btn-primary plant-store-action";
      addButton.textContent = "Add to Cart";
      addButton.addEventListener("click", () => addPlantToCart(plant, addButton));
      const viewDetailsButton = document.createElement("button");
      viewDetailsButton.type = "button";
      viewDetailsButton.className = "btn btn-reset plant-card-details-action";
      viewDetailsButton.textContent = "View Details";
      viewDetailsButton.addEventListener("click", () => openQuickView(plant));
      const actions = document.createElement("div");
      actions.className = "plant-card-actions";
      actions.append(addButton, viewDetailsButton);

      details.append(image, placeholder, name, category, nursery, price);
      card.append(details, actions);
      grid.appendChild(card);
    });
  }

  function renderCart(items) {
    currentCartItems = items;
    cartItems.replaceChildren();
    const totalQuantity = items.reduce((total, item) => total + item.quantity, 0);
    const totalAmount = items.reduce(
      (total, item) => total + Number(item.total_amount),
      0
    );

    cartSummary.textContent = `${totalQuantity} item${totalQuantity === 1 ? "" : "s"}`;
    cartItemCount.textContent = String(totalQuantity);
    cartItemCount.setAttribute(
      "aria-label",
      `${totalQuantity} item${totalQuantity === 1 ? "" : "s"} in cart`
    );
    cartItemCount.hidden = totalQuantity === 0;
    cartSubtotal.textContent = formatPrice(totalAmount);
    cartTotal.textContent = formatPrice(totalAmount);
    checkoutButton.disabled = items.length === 0;
    window.dispatchEvent(
      new CustomEvent("greennest:cart-updated", { detail: { count: totalQuantity } })
    );

    if (items.length === 0) {
      const emptyState = document.createElement("p");
      emptyState.className = "plant-empty";
      emptyState.textContent = "Your cart is empty. Add a plant to get started.";
      cartItems.appendChild(emptyState);
      return;
    }

    for (const item of items) {
      const row = document.createElement("article");
      row.className = "buy-cart-item";
      const imageWrap = document.createElement("div");
      imageWrap.className = "buy-cart-image-wrap";
      const image = document.createElement("img");
      image.className = "buy-cart-image";
      image.alt = item.plant.name;
      image.hidden = !item.plant.image_url;
      if (item.plant.image_url) {
        image.src = new URL(item.plant.image_url, API_ORIGIN).href;
      }
      const imagePlaceholder = document.createElement("span");
      imagePlaceholder.className = "buy-cart-image-placeholder";
      imagePlaceholder.textContent = "🪴";
      image.addEventListener("error", () => {
        image.hidden = true;
        imagePlaceholder.hidden = false;
      }, { once: true });
      imageWrap.append(image, imagePlaceholder);

      const description = document.createElement("div");
      description.className = "buy-cart-description";
      const name = document.createElement("h3");
      name.textContent = item.plant.name;
      const unitPrice = document.createElement("p");
      unitPrice.textContent = `${formatPrice(item.plant.buy_price)} each`;
      const lineTotal = document.createElement("p");
      lineTotal.textContent = `Subtotal: ${formatPrice(item.total_amount)}`;
      description.append(name, unitPrice, lineTotal);

      const controls = document.createElement("div");
      controls.className = "buy-cart-item-controls";
      const decreaseButton = document.createElement("button");
      decreaseButton.className = "btn btn-reset";
      decreaseButton.type = "button";
      decreaseButton.textContent = "−";
      decreaseButton.setAttribute("aria-label", `Decrease ${item.plant.name} quantity`);
      decreaseButton.disabled = item.quantity <= 1;
      decreaseButton.addEventListener("click", () =>
        updateCartItem(item, item.quantity - 1, decreaseButton)
      );
      const quantity = document.createElement("span");
      quantity.textContent = String(item.quantity);
      quantity.setAttribute("aria-label", "Quantity");
      const increaseButton = document.createElement("button");
      increaseButton.className = "btn btn-reset";
      increaseButton.type = "button";
      increaseButton.textContent = "+";
      increaseButton.setAttribute("aria-label", `Increase ${item.plant.name} quantity`);
      increaseButton.disabled = item.quantity >= item.plant.available_quantity;
      increaseButton.addEventListener("click", () =>
        updateCartItem(item, item.quantity + 1, increaseButton)
      );
      controls.append(decreaseButton, quantity, increaseButton);

      const removeButton = document.createElement("button");
      removeButton.className = "btn btn-reset buy-cart-remove";
      removeButton.type = "button";
      removeButton.textContent = "Remove";
      removeButton.addEventListener("click", async () => {
        removeButton.disabled = true;
        try {
          await apiRequest(`/cart/items/${item.id}`, {
            method: "DELETE",
            auth: true,
          });
          setCartFeedback(`${item.plant.name} removed from your cart.`, "success");
          await loadCart();
        } catch (error) {
          setCartFeedback(error.message);
          removeButton.disabled = false;
        }
      });

      row.append(imageWrap, description, controls, removeButton);
      cartItems.appendChild(row);
    }
  }

  async function updateCartItem(item, quantity, button) {
    button.disabled = true;
    try {
      await apiRequest(`/cart/items/${item.id}`, {
        method: "PATCH",
        body: { quantity },
        auth: true,
      });
      setCartFeedback("");
      await loadCart();
    } catch (error) {
      setCartFeedback(error.message);
      button.disabled = false;
    }
  }

  async function loadCart() {
    try {
      const items = await apiRequest("/cart/items", { auth: true });
      renderCart(items);
      return items;
    } catch (error) {
      currentCartItems = [];
      cartItems.replaceChildren();
      cartSummary.textContent = "Cart unavailable";
      cartItemCount.hidden = true;
      checkoutButton.disabled = true;
      setCartFeedback(error.message);
      return null;
    }
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
  closeQuickViewButton.addEventListener("click", () => quickViewDialog.close());
  quickViewDialog.addEventListener("click", (event) => {
    if (event.target === quickViewDialog) quickViewDialog.close();
  });
  quickViewAction.addEventListener("click", () => {
    if (quickViewPlant) {
      void addPlantToCart(quickViewPlant, quickViewAction);
    }
  });
  openCartButton.addEventListener("click", async () => {
    setCartFeedback("");
    cartDialog.showModal();
    await loadCart();
  });
  closeCartButton.addEventListener("click", () => cartDialog.close());
  cartDialog.addEventListener("close", () => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("view") === "cart") {
      url.searchParams.delete("view");
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }
  });
  cartDialog.addEventListener("click", (event) => {
    if (event.target === cartDialog) cartDialog.close();
  });
  checkoutButton.addEventListener("click", async () => {
    const itemsInCart = await loadCart();
    if (!itemsInCart || itemsInCart.length === 0) {
      setCartFeedback("Your cart is empty. Add plants before placing an order.");
      return;
    }
    setCartFeedback("");
    hideMessage();

    const invalidField = Object.values(checkoutFields).find((field) => !field.reportValidity());
    if (invalidField) return;

    checkoutButton.disabled = true;
    checkoutButton.textContent = "Starting secure checkout…";
    try {
      if (currentCartItems.length === 0) {
        setCartFeedback("Your cart is empty. Add plants before placing an order.");
        return;
      }
      const order = await apiRequest("/orders/checkout", {
        method: "POST",
        auth: true,
      });
      const data = await apiRequest("/payment/initiate", {
        method: "POST",
        auth: true,
        body: {
          order_type: "purchase",
          order_id: order.id,
          cart_items: itemsInCart.map((item) => ({
            plant_id: item.plant_id,
            quantity: item.quantity,
          })),
          phone: checkoutFields.phone.value.trim(),
          address: checkoutFields.address.value.trim(),
          city: checkoutFields.city.value.trim(),
          postcode: checkoutFields.postcode.value.trim(),
        },
      });
      window.location.href = data.GatewayPageURL;
    } catch (error) {
      setCartFeedback(error.message);
      checkoutButton.textContent = "Place Order";
      checkoutButton.disabled = false;
    } finally {
      if (checkoutButton.textContent !== "Place Order") {
        checkoutButton.textContent = "Place Order";
      }
      if (cartItems.querySelector(".buy-cart-item")) {
        checkoutButton.disabled = false;
      }
    }
  });
  loadBuyPlants();
  loadBuyPlants();
  if (new URLSearchParams(window.location.search).get("view") === "cart") {
    cartDialog.showModal();
  }
  void loadCart();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "buy") {
    initBuyPage();
  }
});
