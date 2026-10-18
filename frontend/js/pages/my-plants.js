function initMyPlants() {
  const tbody = document.getElementById("myPlantsTableBody");
  const dialog = document.getElementById("editPlantDialog");
  const form = document.getElementById("editPlantForm");
  const saveButton = document.getElementById("savePlantButton");
  let plants = [];
  let selectedPlant = null;

  function openEditForm(plant) {
    selectedPlant = plant;
    document.getElementById("editPlantName").value = plant.name;
    document.getElementById("editPlantCategory").value = plant.category;
    document.getElementById("editPlantSize").value = plant.size || "";
    document.getElementById("editPlantDescription").value = plant.description || "";
    document.getElementById("editPlantBuyPrice").value = plant.buy_price ?? "";
    document.getElementById("editPlantRentPrice").value = plant.rent_price ?? "";
    document.getElementById("editPlantQuantity").value = plant.available_quantity;
    document.getElementById("editPlantAvailability").value = plant.availability_status;
    document.getElementById("editPlantCare").value = plant.care_instructions || "";
    document.getElementById("editPlantImage").value = "";
    const currentImage = document.getElementById("editPlantCurrentImage");
    currentImage.hidden = !plant.image_url;
    if (plant.image_url) {
      currentImage.src = `${API_ORIGIN}${plant.image_url}`;
    } else {
      currentImage.removeAttribute("src");
    }
    document.getElementById("editPlantMessage").className = "alert hidden";
    dialog.showModal();
  }

  function appendOptionalValue(formData, key, value) {
    formData.append(key, value.trim());
  }

  async function loadMyPlants() {
    try {
      plants = await apiRequest("/nurseries/mine/plants", { auth: true });
      tbody.replaceChildren();

      if (plants.length === 0) {
        const row = tbody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 5;
        cell.textContent = "No plants have been added to your nursery yet.";
        return;
      }

      plants.forEach((plant) => {
        const row = tbody.insertRow();
        [plant.name, plant.category, plant.available_quantity, plant.availability_status]
          .forEach((value) => {
            row.insertCell().textContent = value;
          });
        const actionCell = row.insertCell();
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "btn btn-primary";
        editButton.textContent = "Edit";
        editButton.addEventListener("click", () => openEditForm(plant));
        actionCell.appendChild(editButton);
      });
    } catch (error) {
      showMessage(error.message);
      tbody.replaceChildren();
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 5;
      cell.textContent = "Failed to load your plants.";
    }
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!selectedPlant) {
      return;
    }

    const formData = new FormData();
    formData.append("name", document.getElementById("editPlantName").value.trim());
    formData.append("category", document.getElementById("editPlantCategory").value.trim());
    appendOptionalValue(formData, "size", document.getElementById("editPlantSize").value);
    appendOptionalValue(
      formData,
      "description",
      document.getElementById("editPlantDescription").value
    );
    appendOptionalValue(formData, "buy_price", document.getElementById("editPlantBuyPrice").value);
    appendOptionalValue(formData, "rent_price", document.getElementById("editPlantRentPrice").value);
    formData.append("available_quantity", document.getElementById("editPlantQuantity").value);
    formData.append(
      "availability_status",
      document.getElementById("editPlantAvailability").value
    );
    appendOptionalValue(formData, "care_instructions", document.getElementById("editPlantCare").value);
    const imageFile = document.getElementById("editPlantImage").files[0];
    if (imageFile) {
      formData.append("image", imageFile);
    }

    try {
      setLoading(saveButton, true, "Saving...");
      const updatedPlant = await apiRequest(`/plants/${selectedPlant.id}`, {
        method: "PUT",
        auth: true,
        body: formData
      });
      plants = plants.map((plant) => plant.id === updatedPlant.id ? updatedPlant : plant);
      dialog.close();
      showMessage("Plant updated successfully!", "success");
      await loadMyPlants();
    } catch (error) {
      const message = document.getElementById("editPlantMessage");
      message.textContent = error.message;
      message.className = "alert alert-error";
    } finally {
      setLoading(saveButton, false);
    }
  });

  dialog.querySelector(".plant-edit-close").addEventListener("click", () => dialog.close());
  dialog.querySelector(".plant-edit-cancel").addEventListener("click", () => dialog.close());
  loadMyPlants();
}

window.dashboardShell.ready.then(({ user }) => {
  if (user) {
    initMyPlants();
  }
});
