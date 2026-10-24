function initNurseryProfile() {
  const form = document.getElementById("profileForm");
  if (!form) {
    console.error("Profile form not found in DOM!");
    return;
  }
  
  const submitButton = form.querySelector('button[type="submit"]');
  let currentNursery = null;

  // Sidebar avatar update korar helper function
  function updateSidebarAvatar(imageUrl) {
    const sidebarAvatar = document.getElementById("sidebarAvatar");
    if (sidebarAvatar && imageUrl) {
      sidebarAvatar.textContent = "";
      sidebarAvatar.style.backgroundImage = `url("${imageUrl}")`;
      sidebarAvatar.style.backgroundSize = "cover";
      sidebarAvatar.style.backgroundPosition = "center";
      sidebarAvatar.style.backgroundRepeat = "no-repeat";
    }
  }

  async function loadProfile() {
    try {
      const user = await apiRequest("/users/me", { auth: true });
      if (user && user.email) {
        document.getElementById("ownerEmail").value = user.email;
      }
    } catch (error) {
      console.error("User load error:", error);
    }

    try {
      currentNursery = await apiRequest("/nurseries/me", { auth: true });
      if (currentNursery) {
        document.getElementById("nurseryName").value = currentNursery.name || "";
        document.getElementById("ownerEmail").value = currentNursery.email || document.getElementById("ownerEmail").value;
        document.getElementById("contactNumber").value = currentNursery.phone || "";
        document.getElementById("city").value = currentNursery.city || "";
        document.getElementById("location").value = currentNursery.address || "";
        
        // Image preview & Sidebar avatar update
        if (currentNursery.image_url) {
          const imgPreview = document.getElementById("nurseryImagePreview");
          if (imgPreview) {
            imgPreview.src = currentNursery.image_url;
            imgPreview.style.display = "block";
          }
          updateSidebarAvatar(currentNursery.image_url);
        }
        
        console.log("Loaded existing nursery:", currentNursery);
      }
    } catch (error) {
      console.log("No existing profile found (will create new on submit):", error);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
      const formData = new FormData();
      formData.append("name", document.getElementById("nurseryName").value);
      formData.append("email", document.getElementById("ownerEmail").value.trim() || "");
      formData.append("phone", document.getElementById("contactNumber").value);
      formData.append("city", document.getElementById("city").value);
      formData.append("address", document.getElementById("location").value);

      const imageFile = document.getElementById("profileImage").files[0];
      if (imageFile) {
        formData.append("file", imageFile);
      }

      const creatingProfile = !currentNursery || !currentNursery.id;
      if (submitButton) setLoading(submitButton, true, "Saving...");
      
      const endpoint = creatingProfile ? "/nurseries" : `/nurseries/${currentNursery.id}`;
      const method = creatingProfile ? "POST" : "PUT";

      const response = await apiRequest(endpoint, {
        method: method,
        auth: true,
        body: formData
      });

      currentNursery = response;
      if (currentNursery && currentNursery.email) {
        document.getElementById("ownerEmail").value = currentNursery.email;
      }
      
      // Save howar por form preview & Sidebar avatar update
      if (currentNursery && currentNursery.image_url) {
        const imgPreview = document.getElementById("nurseryImagePreview");
        if (imgPreview) {
          imgPreview.src = currentNursery.image_url;
          imgPreview.style.display = "block";
        }
        updateSidebarAvatar(currentNursery.image_url);
      }

      showMessage(
        creatingProfile ? "Profile created successfully!" : "Profile saved successfully!",
        "success"
      );
    } catch (error) {
      console.error("Save error:", error);
      showMessage(error.message || "Failed to save profile", "error");
    } finally {
      if (submitButton) setLoading(submitButton, false);
    }
  });

  loadProfile();
}

document.addEventListener("DOMContentLoaded", () => {
  initNurseryProfile();
});