/* Maintenance page.
   Backend endpoints used (all need the login token):
     GET    /maintenance/schedules/my        list my care tasks
     POST   /maintenance/schedules           add a task
     PATCH  /maintenance/schedules/{id}/complete
     DELETE /maintenance/schedules/{id}
     GET    /maintenance/care-guide          default "how to" tips
     POST   /maintenance/requests            submit a request
     GET    /maintenance/requests/my         list my requests
     PATCH  /maintenance/requests/{id}/cancel
   Helpers from app.js: apiRequest, showMessage, hideMessage, setLoading, formatDate. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const TASK_LABELS = {
    watering: "Watering",
    fertilizing: "Fertilizing",
    pruning: "Pruning",
    repotting: "Repotting",
    pest_control: "Pest control",
    other: "Other",
  };

  const STATUS_LABELS = {
    pending: "Pending",
    completed: "Completed",
    skipped: "Skipped",
    open: "Open",
    in_progress: "In progress",
    resolved: "Resolved",
    cancelled: "Cancelled",
  };

  let schedules = [];
  let requests = [];
  let careTips = {}; // { watering: "Water when...", ... }

  /* =========================================================
     Small helpers
     ========================================================= */
  // Create an element with optional class and text (textContent keeps it XSS-safe)
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // The backend sends dates as "YYYY-MM-DD". Build a LOCAL date from it,
  // because new Date("2026-10-10") is read as UTC and can show the wrong day.
  function parseDate(value) {
    const [year, month, day] = value.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  function startOfToday() {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), now.getDate());
  }

  function isoToday() {
    const t = startOfToday();
    const mm = String(t.getMonth() + 1).padStart(2, "0");
    const dd = String(t.getDate()).padStart(2, "0");
    return `${t.getFullYear()}-${mm}-${dd}`;
  }

  const daysUntil = (value) => Math.round((parseDate(value) - startOfToday()) / 86400000);

  function fmtDay(value) {
    return parseDate(value).toLocaleDateString(undefined, {
      day: "numeric", month: "short", year: "numeric",
    });
  }

  const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

  function badge(cssClass, text) {
    return el("span", `badge ${cssClass}`, text);
  }

  function scrollToMessage() {
    $("message").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Show an error, scroll to it, and stop the calling handler
  function fail(text) {
    showMessage(text);
    scrollToMessage();
  }

  function actionButton(label, className, handler) {
    const button = el("button", className, label);
    button.type = "button";
    button.addEventListener("click", () => handler(button));
    return button;
  }

  function emptyRow(body, columns, text) {
    const tr = el("tr", "empty-row");
    const td = el("td", null, text);
    td.colSpan = columns;
    tr.append(td);
    body.append(tr);
  }

  /* =========================================================
     Summary cards
     ========================================================= */
  function renderStats() {
    const pending = schedules.filter((s) => s.status === "pending");
    $("statPending").textContent = pending.length;
    $("statOverdue").textContent = pending.filter((s) => daysUntil(s.due_date) < 0).length;
    $("statCompleted").textContent = schedules.filter((s) => s.status === "completed").length;
    $("statRequests").textContent = requests.filter(
      (r) => r.status === "open" || r.status === "in_progress"
    ).length;
  }

  /* =========================================================
     Care schedule table
     ========================================================= */
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
      return task.completed_at ? `Done on ${formatDate(task.completed_at)}` : "Completed";
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
    body.replaceChildren();

    const filter = $("statusFilter").value;
    const rows = schedules
      .filter((task) => filter === "all" || task.status === filter)
      .sort((a, b) => {
        // Pending tasks first (soonest due first), then the rest (newest first)
        const aPending = a.status === "pending";
        const bPending = b.status === "pending";
        if (aPending !== bPending) return aPending ? -1 : 1;
        const diff = parseDate(a.due_date) - parseDate(b.due_date);
        return aPending ? diff : -diff;
      });

    if (rows.length === 0) {
      emptyRow(
        body, 7,
        schedules.length === 0
          ? "No care tasks yet. Add your first one below."
          : "No tasks match this filter."
      );
      return;
    }

    rows.forEach((task) => {
      const tr = document.createElement("tr");

      const plantCell = el("td");
      plantCell.append(el("div", "cell-strong", task.plant_name));

      const dueCell = el("td");
      dueCell.append(el("div", "cell-strong", fmtDay(task.due_date)));
      dueCell.append(el("div", "cell-sub", dueHint(task)));

      const repeat = task.frequency_days
        ? `Every ${plural(task.frequency_days, "day")}`
        : "One-time";

      const statusCell = el("td");
      statusCell.append(scheduleBadge(task));

      const actionsCell = el("td");
      const actions = el("div", "actions");
      if (task.status === "pending") {
        actions.append(actionButton("Mark done", "btn btn-primary btn-sm", (btn) => completeTask(task, btn)));
      }
      actions.append(actionButton("Delete", "btn btn-outline danger btn-sm", (btn) => deleteTask(task, btn)));
      actionsCell.append(actions);

      tr.append(
        plantCell,
        el("td", null, TASK_LABELS[task.task_type] || task.task_type),
        dueCell,
        el("td", "cell-text", task.instructions),
        el("td", null, repeat),
        statusCell,
        actionsCell
      );
      body.append(tr);
    });
  }

  async function loadSchedules() {
    schedules = await apiRequest("/maintenance/schedules/my?limit=200", { auth: true });
    renderSchedules();
    renderStats();
  }

  async function completeTask(task, button) {
    hideMessage();
    button.disabled = true;
    try {
      await apiRequest(`/maintenance/schedules/${task.id}/complete`, { method: "PATCH", auth: true });
      showMessage(
        task.frequency_days
          ? "Task marked as done. The next one has been scheduled."
          : "Task marked as done.",
        "success"
      );
      await loadSchedules();
    } catch (err) {
      showMessage(err.message);
      button.disabled = false;
    }
    scrollToMessage();
  }

  async function deleteTask(task, button) {
    const label = TASK_LABELS[task.task_type] || task.task_type;
    if (!window.confirm(`Delete the ${label.toLowerCase()} task for "${task.plant_name}"?`)) return;

    hideMessage();
    button.disabled = true;
    try {
      await apiRequest(`/maintenance/schedules/${task.id}`, { method: "DELETE", auth: true });
      showMessage("Task deleted.", "success");
      await loadSchedules();
    } catch (err) {
      showMessage(err.message);
      button.disabled = false;
    }
    scrollToMessage();
  }

  $("statusFilter").addEventListener("change", renderSchedules);

  /* =========================================================
     Add a care task (default care tip)
     ========================================================= */
  async function loadCareTips() {
    const tips = await apiRequest("/maintenance/care-guide", { auth: true });
    careTips = Object.fromEntries(tips.map((tip) => [tip.task_type, tip.how_to]));
    updateTip();
  }

  function updateTip() {
    const tip = careTips[$("taskType").value];
    $("tipBox").textContent = tip
      ? `If you leave this empty we will use: ${tip}`
      : "Please write your own instructions for this task.";
  }
  $("taskType").addEventListener("change", updateTip);

  $("taskForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const plant_name = $("plantName").value.trim();
    const task_type = $("taskType").value;
    const due_date = $("dueDate").value;
    const instructions = $("instructions").value.trim();
    const frequencyRaw = $("frequency").value.trim();

    // Quick checks here; the backend validates everything again.
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

    // Optional fields are only sent when filled in
    const body = { plant_name, task_type, due_date };
    if (instructions) body.instructions = instructions;
    if (frequency_days) body.frequency_days = frequency_days;

    const button = $("taskSubmitBtn");
    setLoading(button, true, "Adding...");
    try {
      await apiRequest("/maintenance/schedules", { method: "POST", body, auth: true });
      showMessage("Care task added.", "success");
      $("taskForm").reset();
      updateTip();
      await loadSchedules();
    } catch (err) {
      showMessage(err.message);
    } finally {
      setLoading(button, false);
      scrollToMessage();
    }
  });

  /* =========================================================
     Maintenance requests
     ========================================================= */
  function renderRequests() {
    const body = $("requestBody");
    body.replaceChildren();

    if (requests.length === 0) {
      emptyRow(body, 6, "You have not submitted any requests yet.");
      return;
    }

    requests.forEach((request) => {
      const tr = document.createElement("tr");

      const titleCell = el("td");
      titleCell.append(el("div", "cell-strong", TASK_LABELS[request.request_type] || request.request_type));
      titleCell.append(el("div", "cell-sub", request.plant_name || "General request"));

      const statusCell = el("td");
      statusCell.append(badge(request.status, STATUS_LABELS[request.status] || request.status));
      if (request.response_note) {
        statusCell.append(el("div", "cell-sub", `Note: ${request.response_note}`));
      }

      const actionsCell = el("td");
      if (request.status === "open") {
        actionsCell.append(
          actionButton("Cancel", "btn btn-outline danger btn-sm", (btn) => cancelRequest(request, btn))
        );
      }

      tr.append(
        titleCell,
        el("td", "cell-text", request.description),
        el("td", null, request.preferred_date ? fmtDay(request.preferred_date) : "-"),
        statusCell,
        el("td", null, formatDate(request.created_at)),
        actionsCell
      );
      body.append(tr);
    });
  }

  async function loadRequests() {
    requests = await apiRequest("/maintenance/requests/my?limit=200", { auth: true });
    renderRequests();
    renderStats();
  }

  async function cancelRequest(request, button) {
    if (!window.confirm("Cancel this request?")) return;

    hideMessage();
    button.disabled = true;
    try {
      await apiRequest(`/maintenance/requests/${request.id}/cancel`, { method: "PATCH", auth: true });
      showMessage("Request cancelled.", "success");
      await loadRequests();
    } catch (err) {
      showMessage(err.message);
      button.disabled = false;
    }
    scrollToMessage();
  }

  $("requestForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const plant_name = $("requestPlant").value.trim();
    const request_type = $("requestType").value;
    const preferred_date = $("preferredDate").value;
    const description = $("requestDescription").value.trim();

    if (description.length < 10) return fail("Please describe the problem (at least 10 characters).");
    if (description.length > 1000) return fail("The description must be at most 1000 characters.");
    if (preferred_date && preferred_date < isoToday()) return fail("The preferred date cannot be in the past.");

    const body = { request_type, description };
    if (plant_name) body.plant_name = plant_name;
    if (preferred_date) body.preferred_date = preferred_date;

    const button = $("requestSubmitBtn");
    setLoading(button, true, "Submitting...");
    try {
      await apiRequest("/maintenance/requests", { method: "POST", body, auth: true });
      showMessage("Your request has been submitted.", "success");
      $("requestForm").reset();
      await loadRequests();
    } catch (err) {
      showMessage(err.message);
    } finally {
      setLoading(button, false);
      scrollToMessage();
    }
  });

  /* =========================================================
     Start
     ========================================================= */
  $("dueDate").min = isoToday();
  $("preferredDate").min = isoToday();

  (async function init() {
    const results = await Promise.allSettled([loadSchedules(), loadRequests(), loadCareTips()]);
    const failed = results.find((r) => r.status === "rejected");
    if (failed) showMessage(failed.reason.message);
  })();
})();