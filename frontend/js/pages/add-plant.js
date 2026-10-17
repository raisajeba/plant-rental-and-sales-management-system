async function initAddPlant() {
  const form = document.getElementById("addPlantForm");
  const nurserySelect = document.getElementById("nurserySelect");
  const submitButton = form.querySelector('button[type="submit"]');
  const imageInput = document.getElementById("plantImage");

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
    const formData = new FormData();
    formData.append("name", document.getElementById("plantName").value);
    formData.append("category", document.getElementById("plantCategory").value);
    formData.append("buy_price", document.getElementById("buyPrice").value);
    if (rentPriceValue) {
      formData.append("rent_price", rentPriceValue);
    }
    formData.append(
      "available_quantity",
      document.getElementById("quantity").value
    );
    formData.append("description", document.getElementById("description").value);
    formData.append(
      "care_instructions",
      document.getElementById("careInstructions").value
    );
    formData.append(
      "availability_status",
      rentPriceValue && Number(rentPriceValue) > 0
        ? "available_for_both"
        : "available_for_sale"
    );
    if (imageInput.files[0]) {
      formData.append("image", imageInput.files[0]);
    }

    try {
      setLoading(submitButton, true, "Uploading...");
      await apiRequest(`/nurseries/${nurserySelect.value}/plants`, {
        method: "POST",
        auth: true,
        body: formData
      });
      showMessage("Plant successfully uploaded to the nursery marketplace!", "success");
      form.reset();
    } catch (err) {
      showMessage(err.message, "error");
    } finally {
      setLoading(submitButton, false);
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