async function loadMyPlants() {
  const tbody = document.getElementById("myPlantsTableBody");

  try {
    const plants = await apiRequest("/nurseries/mine/plants", { auth: true });
    tbody.replaceChildren();

    if (plants.length === 0) {
      const row = tbody.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.textContent = "No plants have been added to your nursery yet.";
      return;
    }

    plants.forEach((plant) => {
      const row = tbody.insertRow();
      [plant.name, plant.category, plant.available_quantity, plant.availability_status]
        .forEach((value) => {
          row.insertCell().textContent = value;
        });
    });
  } catch (error) {
    showMessage(error.message);
    tbody.replaceChildren();
    const row = tbody.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = "Failed to load your plants.";
  }
}

window.dashboardShell.ready.then(({ user }) => {
  if (user) {
    loadMyPlants();
  }
});
