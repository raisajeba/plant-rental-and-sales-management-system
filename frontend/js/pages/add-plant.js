async function initAddPlant() {
  const form = document.getElementById("addPlantForm");
  const nurserySelect = document.getElementById("nurserySelect");
  const submitButton = form.querySelector('button[type="submit"]');

  try {
    const nurseries = await apiRequest("/nurseries/mine", { auth: true });
    nurserySelect.replaceChildren();

    if (nurseries.length === 0) {
      nurserySelect.add(new Option("Create a nursery profile first", ""));
      submitButton.disabled = true;
      showMessage("Add a nursery profile before listing plants.");
      return;
    }

    nurseries.forEach((nursery) => {
      nurserySelect.add(new Option(nursery.name, nursery.id));
    });
  } catch (error) {
    showMessage(error.message);
    submitButton.disabled = true;
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const rentPriceValue = document.getElementById("rentPrice").value.trim();
    const rentPrice = rentPriceValue ? Number(rentPriceValue) : null;
    const payload = {
      name: document.getElementById("plantName").value,
      category: document.getElementById("plantCategory").value,
      buy_price: Number(document.getElementById("buyPrice").value),
      rent_price: rentPrice,
      available_quantity: Number.parseInt(document.getElementById("quantity").value, 10),
      description: document.getElementById("description").value,
      care_instructions: document.getElementById("careInstructions").value,
      availability_status: rentPrice && rentPrice > 0
        ? "available_for_both"
        : "available_for_sale"
    };

    try {
      await apiRequest(`/nurseries/${nurserySelect.value}/plants`, {
        method: "POST",
        auth: true,
        body: payload
      });
      showMessage("Plant successfully uploaded to the nursery marketplace!", "success");
      form.reset();
    } catch (err) {
      showMessage(err.message, "error");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "add-plant") {
    window.dashboardShell.ready.then(({ user }) => {
      if (user) {
        initAddPlant();
      }
    });
  }
});