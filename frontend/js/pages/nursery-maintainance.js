(function () {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const taskLabels = {
        watering: "Watering",
        fertilizing: "Fertilizing",
        pruning: "Pruning",
        repotting: "Repotting",
        pest_control: "Pest control",
        other: "Other"
    };

    const statuses = ["pending", "completed"];

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
            day: "numeric",
            month: "short",
            year: "numeric"
        });
    }

    function setPlantCustomerOptions() {
        const select = $("plantCustomer");
        if (!select) return;

        select.replaceChildren();

        const placeholder = el(
            "option",
            null,
            plantCustomers.length
                ? "Choose a customer plant"
                : "No associated plants found"
        );

        placeholder.value = "";
        select.append(placeholder);

        plantCustomers.forEach((item) => {
            const option = el(
                "option",
                null,
                `${item.plant_name} (${item.customer_name})`
            );

            option.value = `${item.plant_id}:${item.customer_id}`;
            select.append(option);
        });

        select.disabled = plantCustomers.length === 0;

        const submitButton = $("serviceSubmit");
        if (submitButton) {
            submitButton.disabled = plantCustomers.length === 0;
        }
    }

    function renderRecords() {
        const body = $("nurseryMaintenanceTableBody");
        if (!body) return;

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
            plantCell.append(
                el("div", "cell-strong", record.plant_name || "Nursery request")
            );
            plantCell.append(
                el(
                    "div",
                    "cell-sub",
                    taskLabels[record.request_type] || record.request_type
                )
            );

            const customerCell = el("td", null, record.customer_name);
            const detailsCell = el("td", "cell-text", record.description);
            const dateCell = el("td", null, formatDay(record.preferred_date));

            const statusCell = el("td");
            statusCell.append(
                el(
                    "span",
                    `badge ${record.status}`,
                    record.status.replaceAll("_", " ")
                )
            );

            if (record.response_note) {
                statusCell.append(
                    el("div", "cell-sub", `Note: ${record.response_note}`)
                );
            }

            const updateCell = el("td");
            const controls = el("div", "actions");

            const statusSelect = document.createElement("select");
            statusSelect.setAttribute(
                "aria-label",
                `Status for ${record.plant_name || "nursery request"}`
            );

            if (record.status === "cancelled") {
                const option = el("option", null, "Cancelled");
                option.value = "cancelled";
                statusSelect.append(option);
                statusSelect.disabled = true;
            } else {
                statuses.forEach((status) => {
                    const option = el(
                        "option",
                        null,
                        status.replaceAll("_", " ")
                    );

                    option.value = status;
                    statusSelect.append(option);
                });

                statusSelect.value = record.status;
            }

            const dateInput = document.createElement("input");
            dateInput.type = "date";
            dateInput.value = record.preferred_date || "";
            dateInput.min = localToday();
            dateInput.setAttribute(
                "aria-label",
                `Scheduled date for ${record.plant_name || "nursery request"}`
            );

            const noteInput = document.createElement("input");
            noteInput.type = "text";
            noteInput.maxLength = 500;
            noteInput.value = record.response_note || "";
            noteInput.placeholder = "Response note";
            noteInput.setAttribute(
                "aria-label",
                `Response note for ${record.plant_name || "nursery request"}`
            );

            const save = el("button", "btn btn-primary btn-sm", "Update");
            save.type = "button";
            save.disabled = record.status === "cancelled";

            save.addEventListener("click", () => {
                updateRecord(
                    record,
                    statusSelect,
                    dateInput,
                    noteInput,
                    save
                );
            });

            if (record.status !== "cancelled") {
                controls.append(statusSelect, dateInput, noteInput, save);
            }

            updateCell.append(controls);
            row.append(
                plantCell,
                customerCell,
                detailsCell,
                dateCell,
                statusCell,
                updateCell
            );

            body.append(row);
        });
    }

    async function loadData() {
        try {
            const [plants, loadedRecords] = await Promise.all([
                apiRequest("/maintenance/owner/plant-customers", {
                    auth: true
                }),
                apiRequest("/maintenance/owner/records?limit=200", {
                    auth: true
                })
            ]);

            plantCustomers = plants || [];
            records = loadedRecords || [];

            setPlantCustomerOptions();
            renderRecords();
        } catch (error) {
            console.error("Failed to load nursery maintenance data:", error);
        }
    }

    async function updateRecord(
        record,
        statusSelect,
        dateInput,
        noteInput,
        button
    ) {
        const body = {
            status: statusSelect.value,
            response_note: noteInput.value.trim() || null
        };

        if (dateInput.value !== (record.preferred_date || "")) {
            body.preferred_date = dateInput.value || null;
        }

        button.disabled = true;

        try {
            await apiRequest(
                `/maintenance/owner/records/${record.id}`,
                {
                    method: "PATCH",
                    body,
                    auth: true
                }
            );

            // Reload fresh records directly from backend
            await loadData();

            if (typeof showMessage === "function") {
                showMessage("Maintenance record updated.", "success");
            }
        }
        catch (error) {
            if (typeof showMessage === "function") {
                showMessage(error.message || "Something went wrong", "error");
            }

            button.disabled = false;
        }
    }

    const serviceForm = $("serviceRecordForm");

    if (serviceForm) {
        serviceForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const plantCustomerSelect = $("plantCustomer");
            const plantCustomerVal = plantCustomerSelect
                ? plantCustomerSelect.value
                : "";

            if (!plantCustomerVal) {
                if (typeof showMessage === "function") {
                    showMessage("Choose an associated customer plant.");
                }
                return;
            }

            const [plantId, customerId] = plantCustomerVal
                .split(":")
                .map(Number);

            const description = $("serviceDescription").value.trim();

            if (description.length < 10) {
                if (typeof showMessage === "function") {
                    showMessage(
                        "Maintenance details must be at least 10 characters."
                    );
                }
                return;
            }

            const body = {
                plant_id: plantId,
                customer_id: customerId,
                request_type: $("serviceType").value,
                description,
                preferred_date: $("serviceDate").value || null
            };

            const submitBtn = $("serviceSubmit");

            if (typeof setLoading === "function") {
                setLoading(submitBtn, true, "Creating...");
            }

            try {
                await apiRequest("/maintenance/owner/records", {
                    method: "POST",
                    body,
                    auth: true
                });

                if (typeof showMessage === "function") {
                    showMessage("Maintenance record created.", "success");
                }

                serviceForm.reset();
                await loadData();
            } catch (error) {
                if (typeof showMessage === "function") {
                    showMessage(error.message, "error");
                }
            } finally {
                if (typeof setLoading === "function") {
                    setLoading(submitBtn, false);
                }
            }
        });
    }

    const serviceDateInput = $("serviceDate");

    if (serviceDateInput) {
        serviceDateInput.min = localToday();
    }

    loadData();
})();