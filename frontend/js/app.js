/* =========================================================
   Green Forest frontend: one file, shared by every page.
   Each page sets <body data-page="..."> and the matching
   function at the bottom runs for that page.
   ========================================================= */

// 1. Change this if your backend runs on a different address
const API_BASE = "http://localhost:8000/api/v1";
const TOKEN_KEY = "greennest_token";

/* ---------- Token helpers ---------- */
const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

/* ---------- API helper ---------- */
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Turns FastAPI error bodies into a readable string.
// - Normal errors:    { "detail": "Email is already registered" }
// - Validation (422): { "detail": [ { "loc": [...], "msg": "Value error, ..." } ] }
function extractErrorMessage(data) {
  if (!data || !data.detail) return "Something went wrong. Please try again.";
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((err) => {
        const field = err.loc && err.loc.length > 1 ? err.loc[err.loc.length - 1] : "";
        const msg = String(err.msg).replace(/^Value error, /, "");
        return field ? `${field}: ${msg}` : msg;
      })
      .join("\n");
  }
  return "Something went wrong. Please try again.";
}

// auth = true  ->  sends "Authorization: Bearer <token>"
async function apiRequest(path, { method = "GET", body = null, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };

  if (auth) {
    const token = getToken();
    if (!token) {
      window.location.href = "login.html";
      throw new ApiError("Not logged in", 401);
    }
    headers["Authorization"] = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
  } catch (err) {
    // Network error, or CORS blocked. Check the browser console.
    throw new ApiError("Cannot reach the server. Is the backend running?", 0);
  }

  let data = null;
  try {
    data = await response.json();
  } catch (err) {
    /* response had no JSON body */
  }

  if (!response.ok) {
    // Expired / invalid token on a protected request -> back to login
    if (response.status === 401 && auth) {
      clearToken();
      window.location.href = "login.html";
    }
    throw new ApiError(extractErrorMessage(data), response.status);
  }
  return data;
}

/* ---------- Small UI helpers ---------- */
function showMessage(text, type = "error") {
  const box = document.getElementById("message");
  box.textContent = text; // textContent (not innerHTML) keeps this XSS-safe
  box.className = `alert alert-${type}`;
}

function hideMessage() {
  const box = document.getElementById("message");
  if (box) box.className = "alert hidden";
}

function setLoading(button, isLoading, loadingText) {
  if (isLoading) {
    button.dataset.originalText = button.textContent;
    button.textContent = loadingText;
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

/* =========================================================
   PAGE: index (just redirects)
   ========================================================= */
function initIndexPage() {
  window.location.replace(getToken() ? "profile.html" : "login.html");
}

/* =========================================================
   PAGE: login  ->  POST /auth/login
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

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    if (!isValidEmail(email)) return showMessage("Please enter a valid email address.");
    if (!password) return showMessage("Please enter your password.");

    setLoading(button, true, "Logging in...");
    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: { email, password },
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
   PAGE: register  ->  POST /auth/register
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

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const role = document.getElementById("role").value;
    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    // Quick checks here; the backend validates everything again.
    if (name.length < 2) return showMessage("Name must be at least 2 characters.");
    if (!isValidEmail(email)) return showMessage("Please enter a valid email address.");
    if (password !== confirmPassword) return showMessage("Passwords do not match.");

    setLoading(button, true, "Creating account...");
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { name, email, password, role },
      });
      showMessage("Account created! Redirecting to login...", "success");
      setTimeout(() => (window.location.href = "login.html"), 1500);
    } catch (err) {
      showMessage(err.message);
      setLoading(button, false);
    }
  });
}

/* =========================================================
   PAGE: profile  ->  GET /users/me, PUT /users/me, POST /auth/logout
   ========================================================= */
function initProfilePage() {
  // Not logged in? Go to login.
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  let currentUser = null;

  const form = document.getElementById("profileForm");
  const saveButton = document.getElementById("submitBtn");

  // Fill every place on the page that shows user data
  function renderUser(user) {
    currentUser = user;
    const initial = user.name.trim().charAt(0).toUpperCase();
    const firstName = user.name.trim().split(" ")[0];

    document.getElementById("sidebarAvatar").textContent = initial;
    document.getElementById("sidebarName").textContent = user.name;
    document.getElementById("sidebarRole").textContent = user.role.role_name;
    document.getElementById("welcomeTitle").textContent = `Welcome back, ${firstName}! 🌿`;

    document.getElementById("detailName").textContent = user.name;
    document.getElementById("detailEmail").textContent = user.email;
    document.getElementById("detailRole").textContent = user.role.role_name;
    document.getElementById("detailCreated").textContent = formatDate(user.created_at);
    document.getElementById("detailUpdated").textContent = formatDate(user.updated_at);

    const statusBadge = document.getElementById("detailStatus");
    statusBadge.textContent = user.status;
    statusBadge.className = `badge ${user.status}`;

    document.getElementById("name").value = user.name;
    document.getElementById("email").value = user.email;
  }

  // Load the profile when the page opens
  async function loadProfile() {
    try {
      renderUser(await apiRequest("/users/me", { auth: true }));
    } catch (err) {
      showMessage(err.message);
    }
  }

  // Save changes: send only the fields that actually changed
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    hideMessage();
    if (!currentUser) return;

    const name = document.getElementById("name").value.trim();
    const email = document.getElementById("email").value.trim();
    const changes = {};

    if (name !== currentUser.name) changes.name = name;
    if (email.toLowerCase() !== currentUser.email) changes.email = email;

    if (Object.keys(changes).length === 0) {
      return showMessage("You have not changed anything.", "error");
    }
    if (changes.name !== undefined && name.length < 2) {
      return showMessage("Name must be at least 2 characters.");
    }
    if (changes.email !== undefined && !isValidEmail(email)) {
      return showMessage("Please enter a valid email address.");
    }

    setLoading(saveButton, true, "Saving...");
    try {
      renderUser(await apiRequest("/users/me", { method: "PUT", body: changes, auth: true }));
      showMessage("Profile updated successfully.", "success");
    } catch (err) {
      showMessage(err.message);
    } finally {
      setLoading(saveButton, false);
    }
  });

  // Logout: tell the server to revoke the token, then always clear it locally
  document.getElementById("logoutBtn").addEventListener("click", async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST", auth: true });
    } catch (err) {
      /* even if the request fails, still log out locally */
    }
    clearToken();
    window.location.href = "login.html";
  });

  loadProfile();
}

/* ---------- Run the right code for the current page ---------- */
document.addEventListener("DOMContentLoaded", () => {
  const page = document.body.dataset.page;
  if (page === "index") initIndexPage();
  else if (page === "login") initLoginPage();
  else if (page === "register") initRegisterPage();
  else if (page === "profile") initProfilePage();
});