(function () {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const safeShowMessage = typeof showMessage === "function" ? showMessage : (msg, type) => console.log(`[${type}] ${msg}`);
    const safeHideMessage = typeof hideMessage === "function" ? hideMessage : () => {};
    const safeSetLoading = typeof setLoading === "function" ? setLoading : (btn, loading) => { if (btn) btn.disabled = loading; };
    const safeFormatDate = typeof formatDate === "function" ? formatDate : (date) => (date ? new Date(date).toLocaleDateString() : "");

    const TASK_LABELS = {
        watering: "Watering",
        fertilizing: "Fertilizing",
        pruning: "Pruning",
        repotting: "Repotting",
        pest_control: "Pest control",
        other: "Other"
    };

    const STATUS_LABELS = {
        pending: "Pending",
        completed: "Completed",
        skipped: "Skipped",
        open: "Open",
        in_progress: "In progress",
        resolved: "Completed",
        cancelled: "Cancelled"
    };

    let schedules = [];
    let requests = [];
    let careTips = {};

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined) node.textContent = text;
        return node;
    }

    function parseDate(value) {
        if (!value) return new Date();
        const [year, month, day] = value.split("-").map(Number);
        return new Date(year, month - 1, day);
    }

    function startOfToday() {
        const now = new Date();
        return new Date(now.getFullYear(), now.getMonth(), now.getDate());
    }

    function isoToday() {
        const today = startOfToday();
        const month = String(today.getMonth() + 1).padStart(2, "0");
        const day = String(today.getDate()).padStart(2, "0");
        return `${today.getFullYear()}-${month}-${day}`;
    }

    const daysUntil = (value) => Math.round((parseDate(value) - startOfToday()) / 86400000);

    function fmtDay(value) {
        if (!value) return "-";
        return parseDate(value).toLocaleDateString(undefined, {
            day: "numeric", month: "short", year: "numeric"
        });
    }

    const plural = (number, word) => `${number} ${word}${number === 1 ? "" : "s"}`;

    function badge(cssClass, text) {
        return el("span", `badge ${cssClass}`, text);
    }

    function scrollToMessage() {
        const message = $("message");
        if (message) {
            message.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }
    }

    function fail(text) {
        safeShowMessage(text, "error");
        scrollToMessage();
    }

    function actionButton(label, className, handler) {
        const button = el("button", className, label);
        button.type = "button";
        button.addEventListener("click", () => handler(button));
        return button;
    }

    function emptyRow(body, columns, text) {
        const row = el("tr", "empty-row");
        const cell = el("td", null, text);
        cell.colSpan = columns;
        row.append(cell);
        body.append(row);
    }

    function renderStats() {
        const pending = schedules.filter((s) => s.status === "pending");
        const activeRequests = requests.filter((r) => r.status !== "cancelled");
        const openRequests = activeRequests.filter((r) => r.status === "open");

        if ($("statPending")) {
            $("statPending").textContent = pending.length + openRequests.filter((r) => !r.preferred_date).length;
        }
        if ($("statOverdue")) {
            $("statOverdue").textContent = pending.filter((t) => daysUntil(t.due_date) < 0).length +
                openRequests.filter((r) => r.preferred_date && daysUntil(r.preferred_date) < 0).length;
        }
        if ($("statUpcoming")) {
            $("statUpcoming").textContent = pending.filter((t) => daysUntil(t.due_date) > 0).length +
                openRequests.filter((r) => r.preferred_date && daysUntil(r.preferred_date) > 0).length;
        }
        if ($("statCompleted")) {
            $("statCompleted").textContent = schedules.filter((s) => s.status === "completed").length +
                activeRequests.filter((r) => r.status === "resolved").length;
        }
        if ($("statRequests")) {
            $("statRequests").textContent = activeRequests.filter((r) => r.status === "open" || r.status === "in_progress").length;
        }
    }

    function scheduleBadge(task) {
        if (task.status === "completed") return badge("completed", "Completed");
        if (task.status === "skipped") return badge("skipped", "Skipped");
        const days = daysUntil(task.due_date);
        if (days < 0) return badge("overdue", "Overdue");
        if (days <= 3) return badge("soon", days === 0 ? "Due today" : "Due soon");
        return badge("pending", "Pending");
    }

    function dueHint(task) {
        if (task.status === "completed") {
            return task.completed_at ? `Done on ${safeFormatDate(task.completed_at)}` : "Completed";
        }
        if (task.status !== "pending") return "";
        const days = daysUntil(task.due_date);
        if (days < 0) return `${plural(-days, "day")} overdue`;
        if (days === 0) return "Today";
        if (days === 1) return "Tomorrow";
        return `In ${days} days`;
    }

    function renderSchedules() {
        const body = $("scheduleBody");
        if (!body) return;
        body.replaceChildren();

        const filter = $("statusFilter") ? $("statusFilter").value : "all";
        const rows = schedules
            .filter((task) => filter === "all" || task.status === filter)
            .sort((a, b) => {
                const aPending = a.status === "pending";
                const bPending = b.status === "pending";
                if (aPending !== bPending) return aPending ? -1 : 1;
                const difference = parseDate(a.due_date) - parseDate(b.due_date);
                return aPending ? difference : -difference;
            });

        if (rows.length === 0) {
            emptyRow(body, 7, schedules.length === 0 ? "No care tasks yet. Add your first one below." : "No tasks match this filter.");
            return;
        }

        rows.forEach((task) => {
            const row = document.createElement("tr");
            const plantCell = el("td");
            plantCell.append(el("div", "cell-strong", task.plant_name));

            const dueCell = el("td");
            dueCell.append(el("div", "cell-strong", fmtDay(task.due_date)));
            dueCell.append(el("div", "cell-sub", dueHint(task)));

            const repeat = task.frequency_days ? `Every ${plural(task.frequency_days, "day")}` : "One-time";
            const statusCell = el("td");
            statusCell.append(scheduleBadge(task));

            const actionsCell = el("td");
            const actions = el("div", "actions");

            if (task.status === "pending") {
                actions.append(actionButton("Mark done", "btn btn-primary btn-sm", (btn) => completeTask(task, btn)));
                actions.append(actionButton("Delete", "btn btn-outline danger btn-sm", (btn) => deleteTask(task, btn)));
            }
            actionsCell.append(actions);

            row.append(
                plantCell,
                el("td", null, TASK_LABELS[task.task_type] || task.task_type),
                dueCell,
                el("td", "cell-text", task.instructions),
                el("td", null, repeat),
                statusCell,
                actionsCell
            );
            body.append(row);
        });
    }

    async function loadSchedules() {
        try {
            schedules = (await apiRequest("/maintenance/schedules/my?limit=200", { auth: true })) || [];
            renderSchedules();
            renderStats();
        } catch (error) {
            console.error("Error loading schedules:", error);
        }
    }

    async function completeTask(task, button) {
        safeHideMessage();
        button.disabled = true;
        try {
            await apiRequest(`/maintenance/schedules/${task.id}/complete`, { method: "PATCH", auth: true });
            safeShowMessage(task.frequency_days ? "Task marked as done. The next one has been scheduled." : "Task marked as done.", "success");
            await loadSchedules();
        } catch (error) {
            safeShowMessage(error.message, "error");
            button.disabled = false;
            scrollToMessage();
        }
    }

    async function deleteTask(task, button) {
        const label = TASK_LABELS[task.task_type] || task.task_type;
        if (!window.confirm(`Delete the ${label.toLowerCase()} task for "${task.plant_name}"?`)) return;

        safeHideMessage();
        button.disabled = true;
        try {
            await apiRequest(`/maintenance/schedules/${task.id}`, { method: "DELETE", auth: true });
            safeShowMessage("Task deleted.", "success");
            await loadSchedules();
        } catch (error) {
            safeShowMessage(error.message, "error");
            button.disabled = false;
            scrollToMessage();
        }
    }

    if ($("statusFilter")) {
        $("statusFilter").addEventListener("change", renderSchedules);
    }

    async function loadCareTips() {
        try {
            const tips = (await apiRequest("/maintenance/care-guide", { auth: true })) || [];
            careTips = Object.fromEntries(tips.map((tip) => [tip.task_type, tip.how_to]));
            updateTip();
        } catch (error) {
            console.error("Error loading care tips:", error);
        }
    }

    function updateTip() {
        const taskType = $("taskType");
        const tipBox = $("tipBox");
        if (!taskType || !tipBox) return;

        const tip = careTips[taskType.value];
        tipBox.textContent = tip ? `If you leave this empty we will use: ${tip}` : "Please write your own instructions for this task.";
    }

    if ($("taskType")) {
        $("taskType").addEventListener("change", updateTip);
    }

    async function loadNurseriesDropdown() {
        const select = $("requestNursery");
        if (!select) return;
        try {
            const nurseries = (await apiRequest("/nurseries", { auth: true })) || [];
            select.replaceChildren();

            const placeholder = el("option", null, nurseries.length ? "Choose a nursery (optional)" : "No nurseries found");
            placeholder.value = "";
            select.append(placeholder);

            nurseries.forEach((nursery) => {
                const opt = el("option", null, nursery.name);
                opt.value = nursery.id;
                select.append(opt);
            });
        } catch (err) {
            console.error("Failed to load nurseries dropdown:", err);
            select.replaceChildren();
            const opt = el("option", null, "Select nursery (optional)");
            opt.value = "";
            select.append(opt);
        }
    }

    if ($("taskForm")) {
        $("taskForm").addEventListener("submit", async (event) => {
            event.preventDefault();
            safeHideMessage();

            const plantNameInput = $("plantName");
            const taskTypeInput = $("taskType");
            const dueDateInput = $("dueDate");
            const instructionsInput = $("instructions");
            const frequencyInput = $("frequency");

            if (!plantNameInput || !taskTypeInput || !dueDateInput || !instructionsInput || !frequencyInput) {
                return fail("Some required form fields are missing.");
            }

            const plant_name = plantNameInput.value.trim();
            const task_type = taskTypeInput.value;
            const due_date = dueDateInput.value;
            const instructions = instructionsInput.value.trim();
            const frequencyRaw = frequencyInput.value.trim();

            if (plant_name.length < 2) return fail("Please enter the plant name (at least 2 characters).");
            if (!due_date) return fail("Please choose a due date.");
            if (due_date < isoToday()) return fail("The due date cannot be in the past.");
            if (task_type === "other" && !instructions) return fail("Please write the instructions for an 'Other' task.");
            if (instructions.length > 1000) return fail("Instructions must be at most 1000 characters.");

            let frequency_days = null;
            if (frequencyRaw) {
                frequency_days = Number(frequencyRaw);
                if (!Number.isInteger(frequency_days) || frequency_days < 1 || frequency_days > 365) {
                    return fail("Repeat days must be a whole number between 1 and 365.");
                }
            }

            const body = { plant_name, task_type, due_date };
            if (instructions) body.instructions = instructions;
            if (frequency_days) body.frequency_days = frequency_days;

            const button = $("taskSubmitBtn");
            safeSetLoading(button, true, "Adding...");
                      try {
                await apiRequest("/maintenance/schedules", { method: "POST", body, auth: true });
                safeShowMessage("Care task added.", "success");
                $("taskForm").reset();
                updateTip();
                await loadSchedules();
            } catch (error) {
                safeShowMessage(error.message, "error");
            } finally {
                safeSetLoading(button, false);
                scrollToMessage();
            }
        });

    function renderRequests() {
        const body = $("requestBody");
        if (!body) return;
        body.replaceChildren();

        const activeRequests = requests.filter((r) => r.status !== "cancelled");

        if (activeRequests.length === 0) {
            emptyRow(body, 6, "You have not submitted any active requests.");
            return;
        }

        activeRequests.forEach((request) => {
            const row = document.createElement("tr");
            const titleCell = el("td");

            titleCell.append(el("div", "cell-strong", TASK_LABELS[request.request_type] || request.request_type));
            titleCell.append(el("div", "cell-sub", request.plant_name || "General request"));

            const statusCell = el("td");
            let requestStatusLabel = STATUS_LABELS[request.status] || request.status;
            let requestStatusClass = request.status;

            if (request.status === "open") {
                if (request.preferred_date) {
                    const days = daysUntil(request.preferred_date);
                    requestStatusLabel = days < 0 ? "Overdue" : days === 0 ? "Scheduled today" : "Scheduled";
                    requestStatusClass = days < 0 ? "overdue" : "soon";
                } else {
                    requestStatusLabel = "Pending";
                    requestStatusClass = "pending";
                }
            }

            statusCell.append(badge(requestStatusClass, requestStatusLabel));
            if (request.response_note) {
                statusCell.append(el("div", "cell-sub", `Note: ${request.response_note}`));
            }

            const preferredDateCell = el("td");
            preferredDateCell.append(el("div", request.preferred_date ? "cell-strong" : "", request.preferred_date ? fmtDay(request.preferred_date) : "-"));

            if (request.status === "open" && request.preferred_date) {
                const days = daysUntil(request.preferred_date);
                const hint = days < 0 ? `${plural(-days, "day")} overdue` : days === 0 ? "Today" : days === 1 ? "Tomorrow" : `In ${days} days`;
                preferredDateCell.append(el("div", "cell-sub", hint));
            }

            const actionsCell = el("td");
            if (request.status === "open") {
                actionsCell.append(actionButton("Cancel", "btn btn-outline danger btn-sm", (btn) => cancelRequest(request, btn)));
            }

            row.append(
                titleCell,
                el("td", "cell-text", request.description),
                preferredDateCell,
                statusCell,
                el("td", null, safeFormatDate(request.created_at)),
                actionsCell
            );
            body.append(row);
        });
    }

    async function loadRequests() {
        try {
            requests = (await apiRequest("/maintenance/requests/my?limit=200", { auth: true })) || [];
            renderRequests();
            renderStats();
        } catch (error) {
            console.warn("Could not load requests (Backend 503/Unavailable):", error);
            requests = [];
            renderRequests();
            renderStats();
        }
    }

    async function cancelRequest(request, button) {
        if (!window.confirm("Cancel this request?")) return;

        safeHideMessage();
        button.disabled = true;
        try {
            await apiRequest(`/maintenance/requests/${request.id}/cancel`, { method: "PATCH", auth: true });
            safeShowMessage("Request cancelled.", "success");
            await loadRequests();
        } catch (error) {
            safeShowMessage(error.message, "error");
            button.disabled = false;
            scrollToMessage();
        }
    }

    const requestForm = $("requestForm");
    if (requestForm) {
        requestForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            safeHideMessage();

            const plantInput = $("requestPlant");
            const nurseryInput = $("requestNursery");
            const requestTypeInput = $("requestType");
            const preferredDateInput = $("preferredDate");
            const descriptionInput = $("requestDescription");

            if (!requestTypeInput || !preferredDateInput || !descriptionInput) {
                return fail("Some required request form fields are missing.");
            }

            const plant_name_val = plantInput ? plantInput.value.trim() : "";
            const nursery_val = nurseryInput ? nurseryInput.value.trim() : "";
            
            // Combine plant name and nursery name safely so backend doesn't crash on nursery lookup
            let final_plant_name = plant_name_val;
            if (nursery_val) {
                final_plant_name = plant_name_val ? `${plant_name_val} (${nursery_val})` : nursery_val;
            }

            const request_type = requestTypeInput.value;
            const preferred_date = preferredDateInput.value;
            const description = descriptionInput.value.trim();

            if (description.length < 10) return fail("Please describe the problem (at least 10 characters).");
            if (description.length > 1000) return fail("The description must be at most 1000 characters.");
            if (preferred_date && preferred_date < isoToday()) return fail("The preferred date cannot be in the past.");

            // Send only universally accepted fields (plant_name, request_type, description, preferred_date)
            const body = { 
                request_type, 
                description 
            };
            if (final_plant_name) body.plant_name = final_plant_name;
            if (preferred_date) body.preferred_date = preferred_date;

            const button = $("requestSubmitBtn");
            safeSetLoading(button, true, "Submitting...");
            try {
                await apiRequest("/maintenance/requests", { method: "POST", body, auth: true });
                safeShowMessage("Your request has been submitted successfully.", "success");
                requestForm.reset();
                await loadRequests();
            } catch (error) {
                console.error("Maintenance Request Error:", error);
                safeShowMessage(error.message || "Failed to submit request.", "error");
            } finally {
                safeSetLoading(button, false);
                scrollToMessage();
            }
        });
    }
    if ($("dueDate")) $("dueDate").min = isoToday();
    if ($("preferredDate")) $("preferredDate").min = isoToday();

    (async function init() {
        await Promise.allSettled([
            loadSchedules(),
            loadCareTips(),
            loadNurseriesDropdown()
        ]);
        // Load requests separately so 503 doesn't break other features
        await loadRequests();
    })();
}})();