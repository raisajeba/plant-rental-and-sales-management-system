/* =========================================================
   Green Forest frontend: one file, shared by every page.
   Each page sets <body data-page="..."> and the matching
   function at the bottom runs for that page.
   ========================================================= */

// Backend API
const API_BASE = "http://127.0.0.1:8000/api/v1";
const TOKEN_KEY = "greennest_token";

// Full backend URL for uploaded files
const API_ORIGIN = "http://127.0.0.1:8000";


/* ---------- Token helpers ---------- */
const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);


/* ---------- API Error ---------- */
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}


/* ---------- Error message helper ---------- */
function extractErrorMessage(data) {
  if (!data || !data.detail) {
    return "Something went wrong. Please try again.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data.detail)) {
    return data.detail
      .map((err) => {
        const field =
          err.loc && err.loc.length > 1
            ? err.loc[err.loc.length - 1]
            : "";

        const msg = String(err.msg).replace(/^Value error, /, "");

        return field ? `${field}: ${msg}` : msg;
      })
      .join("\n");
  }

  return "Something went wrong. Please try again.";
}


/* =========================================================
   API helper

   JSON body:
   apiRequest("/users/me", {
      method: "PUT",
      body: {...},
      auth: true
   })

   FormData body:
   apiRequest("/users/me", {
      method: "PUT",
      body: formData,
      auth: true
   })
   ========================================================= */
async function apiRequest(
  path,
  { method = "GET", body = null, auth = false } = {}
) {
  const headers = {};

  if (auth) {
    const token = getToken();

    if (!token) {
      window.location.href = "login.html";
      throw new ApiError("Not logged in", 401);
    }

    headers["Authorization"] = `Bearer ${token}`;
  }

  // Only add JSON Content-Type when body is NOT FormData.
  // Browser automatically sets multipart/form-data boundary for FormData.
  if (!(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body:
        body instanceof FormData
          ? body
          : body
            ? JSON.stringify(body)
            : null,
    });
  } catch (err) {
    throw new ApiError(
      "Cannot reach the server. Is the backend running?",
      0
    );
  }

  let data = null;

  try {
    data = await response.json();
  } catch (err) {
    // Response had no JSON body
  }

  if (!response.ok) {
    if (response.status === 401 && auth) {
      clearToken();
      window.location.href = "login.html";
    }

    throw new ApiError(
      extractErrorMessage(data),
      response.status
    );
  }

  return data;
}


/* ---------- UI helpers ---------- */
function showMessage(text, type = "error") {
  const box = document.getElementById("message");

  if (!box) return;

  box.textContent = text;
  box.className = `alert alert-${type}`;
}


function hideMessage() {
  const box = document.getElementById("message");

  if (box) {
    box.className = "alert hidden";
  }
}


function setLoading(button, isLoading, loadingText) {
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
  } else {
    button.textContent =
      button.dataset.originalText || button.textContent;

    button.disabled = false;
  }
}


function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}


const isValidEmail = (email) =>
  /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);


/* =========================================================
   Profile image helper
   ========================================================= */
function getProfileImageUrl(profileImage) {
  if (!profileImage) return null;

  // If backend already returns a full URL
  if (profileImage.startsWith("http://") ||
      profileImage.startsWith("https://")) {
    return profileImage;
  }

  return `${API_ORIGIN}${profileImage}`;
}


/* =========================================================
   PAGE: index
   ========================================================= */
function initIndexPage() {
  window.location.replace(
    getToken() ? "profile.html" : "login.html"
  );
}


/* =========================================================
   PAGE: login
   ========================================================= */
function initLoginPage() {
  if (getToken()) {
    window.location.replace("profile.html");
    return;
  }

  const form = document.getElementById("loginForm");
  const button = document.getElementById("submitBtn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const email =
      document.getElementById("email").value.trim();

    const password =
      document.getElementById("password").value;

    if (!isValidEmail(email)) {
      return showMessage(
        "Please enter a valid email address."
      );
    }

    if (!password) {
      return showMessage(
        "Please enter your password."
      );
    }

    setLoading(button, true, "Logging in...");

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: {
          email,
          password,
        },
      });

      setToken(data.access_token);

      window.location.href = "profile.html";
    } catch (err) {
      showMessage(err.message);
      setLoading(button, false);
    }
  });
}


/* =========================================================
   PAGE: register
   ========================================================= */
function initRegisterPage() {
  if (getToken()) {
    window.location.replace("profile.html");
    return;
  }

  const form = document.getElementById("registerForm");
  const button = document.getElementById("submitBtn");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    const name =
      document.getElementById("name").value.trim();

    const email =
      document.getElementById("email").value.trim();

    const role =
      document.getElementById("role").value;

    const password =
      document.getElementById("password").value;

    const confirmPassword =
      document.getElementById("confirmPassword").value;

    if (name.length < 2) {
      return showMessage(
        "Name must be at least 2 characters."
      );
    }

    if (!isValidEmail(email)) {
      return showMessage(
        "Please enter a valid email address."
      );
    }

    if (password !== confirmPassword) {
      return showMessage(
        "Passwords do not match."
      );
    }

    setLoading(
      button,
      true,
      "Creating account..."
    );

    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: {
          name,
          email,
          password,
          role,
        },
      });

      showMessage(
        "Account created! Redirecting to login...",
        "success"
      );

      setTimeout(
        () => (window.location.href = "login.html"),
        1500
      );
    } catch (err) {
      showMessage(err.message);
      setLoading(button, false);
    }
  });
}


/* =========================================================
   PAGE: profile
   GET /users/me
   PUT /users/me
   POST /auth/logout
   ========================================================= */
function initProfilePage() {
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  let currentUser = null;

  const form =
    document.getElementById("profileForm");

  const saveButton =
    document.getElementById("submitBtn");

  const profileImageInput =
    document.getElementById("profileImage");


  /* -------------------------------------------------------
     Render user
     ------------------------------------------------------- */
  function renderUser(user) {
    currentUser = user;

    const initial =
      user.name.trim().charAt(0).toUpperCase();

    const firstName =
      user.name.trim().split(" ")[0];


    /* Sidebar */
    const sidebarAvatar =
      document.getElementById("sidebarAvatar");

    const imageUrl =
      getProfileImageUrl(user.profile_image);


    if (imageUrl) {
      sidebarAvatar.textContent = "";
      sidebarAvatar.style.backgroundImage =
        `url("${imageUrl}")`;

      sidebarAvatar.style.backgroundSize = "cover";
      sidebarAvatar.style.backgroundPosition = "center";
      sidebarAvatar.style.backgroundRepeat = "no-repeat";
    } else {
      sidebarAvatar.style.backgroundImage = "none";
      sidebarAvatar.textContent = initial;
    }


    document.getElementById("sidebarName").textContent =
      user.name;

    document.getElementById("sidebarRole").textContent =
      user.role.role_name;


    /* Welcome */
    document.getElementById("welcomeTitle").textContent =
      `Welcome back, ${firstName}! 🌿`;


    /* Account details */
    document.getElementById("detailName").textContent =
      user.name;

    document.getElementById("detailEmail").textContent =
      user.email;

    document.getElementById("detailRole").textContent =
      user.role.role_name;

    document.getElementById("detailCreated").textContent =
      formatDate(user.created_at);

    document.getElementById("detailUpdated").textContent =
      formatDate(user.updated_at);


    /* Status */
    const statusBadge =
      document.getElementById("detailStatus");

    statusBadge.textContent = user.status;
    statusBadge.className =
      `badge ${user.status}`;


    /* Form */
    document.getElementById("name").value =
      user.name;

    document.getElementById("email").value =
      user.email;
  }


  /* -------------------------------------------------------
     Load profile
     ------------------------------------------------------- */
  async function loadProfile() {
    try {
      const user =
        await apiRequest("/users/me", {
          auth: true,
        });

      renderUser(user);
    } catch (err) {
      showMessage(err.message);
    }
  }


  /* -------------------------------------------------------
     Save profile
     ------------------------------------------------------- */
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();

    if (!currentUser) return;


    const name =
      document.getElementById("name").value.trim();

    const email =
      document.getElementById("email").value.trim();

    const selectedImage =
      profileImageInput
        ? profileImageInput.files[0]
        : null;


    /* Basic validation */
    if (name.length < 2) {
      return showMessage(
        "Name must be at least 2 characters."
      );
    }

    if (!isValidEmail(email)) {
      return showMessage(
        "Please enter a valid email address."
      );
    }


    /*
     * Check whether anything changed.
     */
    const nameChanged =
      name !== currentUser.name;

    const emailChanged =
      email.toLowerCase() !==
      currentUser.email.toLowerCase();

    const imageChanged =
      selectedImage !== undefined &&
      selectedImage !== null;


    if (
      !nameChanged &&
      !emailChanged &&
      !imageChanged
    ) {
      return showMessage(
        "You have not changed anything.",
        "error"
      );
    }


    /* -----------------------------------------------------
       Create FormData

       Backend expects:
       name
       email
       profile_image
       ----------------------------------------------------- */
    const formData = new FormData();

    if (nameChanged) {
      formData.append("name", name);
    }

    if (emailChanged) {
      formData.append("email", email);
    }

    if (imageChanged) {
      formData.append(
        "profile_image",
        selectedImage
      );
    }


    setLoading(
      saveButton,
      true,
      "Saving..."
    );


    try {
      const updatedUser =
        await apiRequest("/users/me", {
          method: "PUT",
          body: formData,
          auth: true,
        });


      renderUser(updatedUser);


      /*
       * Clear file input after successful upload
       */
      if (profileImageInput) {
        profileImageInput.value = "";
      }


      showMessage(
        "Profile updated successfully.",
        "success"
      );
    } catch (err) {
      showMessage(err.message);
    } finally {
      setLoading(
        saveButton,
        false
      );
    }
  });


  /* -------------------------------------------------------
     Logout
     ------------------------------------------------------- */
  document
    .getElementById("logoutBtn")
    .addEventListener(
      "click",
      async () => {
        try {
          await apiRequest(
            "/auth/logout",
            {
              method: "POST",
              auth: true,
            }
          );
        } catch (err) {
          /* Still logout locally */
        }

        clearToken();
        window.location.href = "login.html";
      }
    );


  loadProfile();
}


/* =========================================================
   Run correct page code
   ========================================================= */
document.addEventListener(
  "DOMContentLoaded",
  () => {
    const page =
      document.body.dataset.page;

    if (page === "index") {
      initIndexPage();
    } else if (page === "login") {
      initLoginPage();
    } else if (page === "register") {
      initRegisterPage();
    } else if (page === "profile") {
      initProfilePage();
    }
  }
);