/* Plants / Rent / Buy placeholder pages.
   Calls the endpoint in <body data-endpoint="..."> and shows the backend's
   { feature, status, message, items } response. */
(function () {
  "use strict";

  const endpoint = document.body.dataset.endpoint;
  const box = document.getElementById("featureBox");
  if (!endpoint || !box) return;

  function render(data) {
    box.replaceChildren();

    const icon = document.createElement("div");
    icon.className = "state-icon";
    icon.textContent = document.body.dataset.icon || "🌱";

    const title = document.createElement("h2");
    title.textContent = data.feature;

    const text = document.createElement("p");
    text.textContent = data.message;

    box.append(icon, title);

    if (data.status === "under_development") {
      const badge = document.createElement("span");
      badge.className = "badge dev";
      badge.textContent = "Under development";
      box.append(badge);
    }
    box.append(text);

    // TODO (next sprint): when the backend returns real data,
    // render data.items here (cards for plants, orders, rentals...).
  }

  async function load() {
    try {
      render(await apiRequest(endpoint, { auth: true }));
    } catch (err) {
      box.replaceChildren();
      showMessage(err.message);
    }
  }

  load();
})();