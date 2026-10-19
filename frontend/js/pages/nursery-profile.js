function initNurseryProfile() {
  const form = document.getElementById("profileForm");
  const submitButton = form.querySelector('button[type="submit"]');
  let currentNursery = null;

  async function loadProfile() {
    try {
      const user = await apiRequest("/users/me", { auth: true });
      document.getElementById("ownerEmail").value = user.email;
    } catch (error) {
      showMessage(error.message, "error");
      return;
    }

    try {
      currentNursery = await apiRequest("/nurseries/me", { auth: true });
      document.getElementById("nurseryName").value = currentNursery.name;
      document.getElementById("ownerEmail").value =
        currentNursery.email || document.getElementById("ownerEmail").value;
      document.getElementById("contactNumber").value = currentNursery.phone;
      document.getElementById("city").value = currentNursery.city;
      document.getElementById("location").value = currentNursery.address;
    } catch (error) {
      if (error.status !== 404) {
        showMessage(error.message, "error");
      }
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
      const payload = {
        name: document.getElementById("nurseryName").value,
        email: document.getElementById("ownerEmail").value.trim() || null,
        phone: document.getElementById("contactNumber").value,
        city: document.getElementById("city").value,
        address: document.getElementById("location").value
      };
      const creatingProfile = currentNursery === null;
      setLoading(submitButton, true, "Saving...");
      currentNursery = await apiRequest(
        creatingProfile ? "/nurseries" : `/nurseries/${currentNursery.id}`,
        {
          method: creatingProfile ? "POST" : "PUT",
          auth: true,
          body: payload
        }
      );
      document.getElementById("ownerEmail").value =
        currentNursery.email || payload.email || "";
      showMessage(
        creatingProfile ? "Profile created successfully!" : "Profile saved successfully!",
        "success"
      );
    } catch (error) {
      showMessage(error.message, "error");
    } finally {
      setLoading(submitButton, false);
    }
  });

  loadProfile();
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.body.dataset.page === "nursery-profile") {
    window.dashboardShell.ready.then(({ user }) => {
      if (user) {
        initNurseryProfile();
      }
    });
  }
});