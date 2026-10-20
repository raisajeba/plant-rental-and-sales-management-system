(() => {
  "use strict";

  const API_BASE = (
    window.GRENNEST_API_URL ||
    `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8000/api/v1`
  ).replace(/\/$/, "");
  const TOKEN_KEY = "greennest_admin_token";
  const token = () => sessionStorage.getItem(TOKEN_KEY);
  const storeToken = (value) => sessionStorage.setItem(TOKEN_KEY, value);
  const clearToken = () => sessionStorage.removeItem(TOKEN_KEY);

  function showMessage(message, type = "danger") {
    const box = document.getElementById("adminMessage");
    if (!box) return;
    box.textContent = message;
    box.className = `alert alert-${type}`;
  }

  async function request(path, { method = "GET", body, authenticated = true } = {}) {
    const headers = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (authenticated) {
      const currentToken = token();
      if (!currentToken) {
        const error = new Error("Please sign in with an administrator account.");
        error.status = 401;
        throw error;
      }
      headers.Authorization = `Bearer ${currentToken}`;
    }

    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch {
      throw new Error("Cannot reach the server. Please try again.");
    }

    let data = null;
    try {
      data = await response.json();
    } catch {
      // A successful response may have no body.
    }
    if (!response.ok) {
      const error = new Error(
        typeof data?.detail === "string"
          ? data.detail
          : "Something went wrong. Please try again."
      );
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function validateAdminSession() {
    if (!token()) return false;
    try {
      await request("/admin/users?limit=1");
      return true;
    } catch (error) {
      if (error.status === 401 || error.status === 403) clearToken();
      return false;
    }
  }

  async function initLogin() {
    if (await validateAdminSession()) {
      window.location.replace("admin-dashboard.html");
      return;
    }

    const form = document.getElementById("adminLoginForm");
    const button = document.getElementById("adminLoginButton");
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const email = document.getElementById("adminEmail").value.trim();
      const password = document.getElementById("adminPassword").value;
      button.disabled = true;
      button.textContent = "Signing in…";

      try {
        const result = await request("/admin/login", {
          method: "POST",
          body: { email, password },
          authenticated: false,
        });
        if (result.user?.role?.role_name !== "Admin") {
          throw new Error("Administrator access is required.");
        }
        storeToken(result.access_token);
        window.location.assign("admin-dashboard.html");
      } catch (error) {
        showMessage(error.message);
        button.disabled = false;
        button.textContent = "Sign in";
      }
    });
  }

  async function loadUsers() {
    const tableBody = document.getElementById("adminUsers");
    const refreshButton = document.getElementById("refreshUsersButton");
    refreshButton.disabled = true;
    try {
      const users = await request("/admin/users?limit=200");
      tableBody.replaceChildren();
      if (!users.length) {
        const row = tableBody.insertRow();
        const cell = row.insertCell();
        cell.colSpan = 4;
        cell.className = "text-secondary text-center py-4";
        cell.textContent = "No accounts to display.";
        return;
      }
      for (const user of users) {
        const row = tableBody.insertRow();
        for (const value of [
          user.name,
          user.email,
          user.role?.role_name || "Unknown",
          user.status,
        ]) {
          const cell = row.insertCell();
          cell.textContent = value;
        }
      }
    } catch (error) {
      if (error.status === 401 || error.status === 403) {
        clearToken();
        window.location.replace("admin-login.html");
        return;
      }
      tableBody.replaceChildren();
      showMessage(error.message);
    } finally {
      refreshButton.disabled = false;
    }
  }

  async function initDashboard() {
    if (!token()) {
      window.location.replace("admin-login.html");
      return;
    }
    document.getElementById("refreshUsersButton").addEventListener("click", loadUsers);
    document.getElementById("adminLogoutButton").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        await request("/auth/logout", { method: "POST" });
        clearToken();
        window.location.replace("admin-login.html");
      } catch (error) {
        if (error.status === 401 || error.status === 403) {
          clearToken();
          window.location.replace("admin-login.html");
          return;
        }
        showMessage(`${error.message} Your session is still active; please retry sign out.`);
        button.disabled = false;
      }
    });
    await loadUsers();
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (document.getElementById("adminLoginForm")) {
      void initLogin();
    } else if (document.getElementById("adminUsers")) {
      void initDashboard();
    }
  });
})();
