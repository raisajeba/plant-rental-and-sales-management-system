function initNurseryProfile() {
  const form = document.getElementById("profileForm");
  let currentNursery = null;

  async function loadProfile() {
    try {
      const [user, nursery] = await Promise.all([
        apiRequest("/users/me", { auth: true }),
        apiRequest("/nurseries/me", { auth: true })
      ]);
      currentNursery = nursery;
      document.getElementById("nurseryName").value = nursery.name;
      document.getElementById("ownerEmail").value = user.email;
      document.getElementById("contactNumber").value = nursery.phone;
      document.getElementById("location").value = nursery.address;
    } catch (error) {
      showMessage(error.message, "error");
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!currentNursery) {
      return;
    }

    try {
      const payload = {
        name: document.getElementById("nurseryName").value,
        phone: document.getElementById("contactNumber").value,
        address: document.getElementById("location").value
      };
      currentNursery = await apiRequest(`/nurseries/${currentNursery.id}`, {
        method: "PUT",
        auth: true,
        body: payload
      });
      showMessage("Profile updated successfully!", "success");
    } catch (error) {
      showMessage(error.message, "error");
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