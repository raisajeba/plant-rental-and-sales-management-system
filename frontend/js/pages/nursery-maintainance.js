(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const taskLabels = {
    watering: "Watering",
    fertilizing: "Fertilizing",
    pruning: "Pruning",
    repotting: "Repotting",
    pest_control: "Pest control",
    other: "Other",
  };
  const statuses = ["pending", "scheduled", "in_progress", "completed"];
  let plantCustomers = [];
  let records = [];

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function localToday() {
    const today = new Date();
    const month = String(today.getMonth() + 1).padStart(2, "0");
    const day = String(today.getDate()).padStart(2, "0");
    return `${today.getFullYear()}-${month}-${day}`;
  }

  function formatDay(value) {
    if (!value) return "Not scheduled";
    return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
      day: "numeric", month: "short", year: "numeric",
    });
  }

  function setPlantCustomerOptions() {
    const select = $("plantCustomer");
    select.replaceChildren();
    const placeholder = el("option", null, plantCustomers.length
      ? "Choose a customer plant"
      : "No associated plants found");
    placeholder.value = "";
    select.append(placeholder);
    plantCustomers.forEach((item) => {
      const option = el("option", null, `${item.plant_name} - ${item.customer_name}`);
      option.value = `${item.plant_id}:${item.customer_id}`;
      select.append(option);
    });
    select.disabled = plantCustomers.length === 0;
    $("serviceSubmit").disabled = plantCustomers.length === 0;
  }

  function renderRecords() {
    const body = $("nurseryMaintenanceTableBody");
    body.replaceChildren();
    if (!records.length) {
      const row = el("tr", "empty-row");
      const cell = el("td", null, "No maintenance records found.");
      cell.colSpan = 6;
      row.append(cell);
      body.append(row);
      return;
    }

    records.forEach((record) => {
      const row = document.createElement("tr");
      const plantCell = el("td");
      plantCell.append(el("div", "cell-strong", record.plant_name));
      plantCell.append(el("div", "cell-sub", taskLabels[record.request_type] || record.request_type));

      const statusCell = el("td");
      statusCell.append(el("span", `badge ${record.status}`, record.status.replaceAll("_", " ")));
      if (record.response_note) statusCell.append(el("div", "cell-sub", record.response_note));

      const updateCell = el("td");
      const controls = el("div", "actions");
      const statusSelect = document.createElement("select");
      statusSelect.setAttribute("aria-label", `Status for ${record.plant_name}`);
      if (record.status === "cancelled") {
        const option = el("option", null, "Cancelled");
        option.value = "cancelled";
        statusSelect.append(option);
        statusSelect.disabled = true;
      } else {
        statuses.forEach((status) => {
          const option = el("option", null, status.replaceAll("_", " "));
          option.value = status;
          statusSelect.append(option);
        });
        statusSelect.value = record.status;
      }

      const dateInput = document.createElement("input");
      dateInput.type = "date";
      dateInput.value = record.preferred_date || "";
      dateInput.min = localToday();
      dateInput.setAttribute("aria-label", `Scheduled date for ${record.plant_name}`);

      const noteInput = document.createElement("input");
      noteInput.type = "text";
      noteInput.maxLength = 500;
      noteInput.value = record.response_note || "";
      noteInput.placeholder = "Response note";
      noteInput.setAttribute("aria-label", `Response note for ${record.plant_name}`);

      const save = el("button", "btn btn-primary btn-sm", "Update");
      save.type = "button";
      save.disabled = record.status === "cancelled";
      save.addEventListener("click", () => updateRecord(record, statusSelect, dateInput, noteInput, save));
      controls.append(statusSelect, dateInput, noteInput, save);
      updateCell.append(controls);

      row.append(
        plantCell,
        el("td", null, record.customer_name),
        el("td", "cell-text", record.description),
        el("td", null, formatDay(record.preferred_date)),
        statusCell,
        updateCell
      );
      body.append(row);
    });
  }

  async function loadData() {
    const [plants, loadedRecords] = await Promise.all([
      apiRequest("/maintenance/owner/plant-customers", { auth: true }),
      apiRequest("/maintenance/owner/records?limit=200", { auth: true }),
    ]);
    plantCustomers = plants;
    records = loadedRecords;
    setPlantCustomerOptions();
    renderRecords();
  }

  async function updateRecord(record, statusSelect, dateInput, noteInput, button) {
    const body = {
      status: statusSelect.value,
      response_note: noteInput.value.trim() || null,
    };
    if (dateInput.value !== (record.preferred_date || "")) {
      body.preferred_date = dateInput.value || null;
    }
    button.disabled = true;
    try {
      const updated = await apiRequest(`/maintenance/owner/records/${record.id}`, {
        method: "PATCH", body, auth: true,
      });
      records = records.map((item) => item.id === updated.id ? updated : item);
      renderRecords();
      showMessage("Maintenance record updated.", "success");
    } catch (error) {
      showMessage(error.message);
      button.disabled = false;
    }
  }

  $("serviceRecordForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const [plantId, customerId] = $("plantCustomer").value.split(":").map(Number);
    const description = $("serviceDescription").value.trim();
    if (!plantId || !customerId) {
      showMessage("Choose an associated customer plant.");
      return;
    }
    if (description.length < 10) {
      showMessage("Maintenance details must be at least 10 characters.");
      return;
    }

    const body = {
      plant_id: plantId,
      customer_id: customerId,
      request_type: $("serviceType").value,
      description,
      preferred_date: $("serviceDate").value || null,
    };
    setLoading($("serviceSubmit"), true, "Creating...");
    try {
      await apiRequest("/maintenance/owner/records", { method: "POST", body, auth: true });
      showMessage("Maintenance record created.", "success");
      $("serviceRecordForm").reset();
      await loadData();
    } catch (error) {
      showMessage(error.message);
    } finally {
      setLoading($("serviceSubmit"), false);
    }
  });

  $("serviceDate").min = localToday();
  loadData().catch((error) => showMessage(error.message));
})();