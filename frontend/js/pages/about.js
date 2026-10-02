/* About Us page: GET /about  ->  { app_name, tagline, description, mission, features[], contact_email } */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  function renderAbout(data) {
    $("aboutTitle").textContent = `About ${data.app_name}`;
    $("aboutTagline").textContent = data.tagline;
    $("aboutDescription").textContent = data.description;
    $("aboutMission").textContent = data.mission;

    // Feature list (textContent only, so no HTML can be injected)
    const list = $("aboutFeatures");
    list.replaceChildren();
    data.features.forEach((feature) => {
      const li = document.createElement("li");
      li.textContent = feature;
      list.append(li);
    });

    // Only turn the address into a mailto: link if it looks like an email
    if (isValidEmail(data.contact_email)) {
      const link = $("aboutEmail");
      link.href = `mailto:${data.contact_email}`;
      link.textContent = data.contact_email;
    }
  }

  async function load() {
    try {
      // Public endpoint: no token needed
      renderAbout(await apiRequest("/about"));
    } catch (err) {
      showMessage(err.message);
      $("aboutTagline").textContent = "Information is unavailable right now.";
      $("aboutDescription").textContent = "-";
      $("aboutMission").textContent = "-";
      $("aboutFeatures").replaceChildren();
    }
  }

  load();
})();