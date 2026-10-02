/* =========================================================
   Shared dashboard layout: sidebar, menu, user card, logout.

   Used by every page that has <body data-layout="dashboard">
   and an empty <aside class="sidebar" id="sidebar"></aside>.

   SCRIPT ORDER MATTERS (at the bottom of each page):
     1. js/app.js     (API helpers)
     2. js/layout.js  (this file)
     3. the page's own script, if it has one
   ========================================================= */
(function () {
  "use strict";

  const body = document.body;
  if (body.dataset.layout !== "dashboard") return;

  // Not logged in? Go to login.
  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const sidebar = document.getElementById("sidebar");
  if (!sidebar) {
    console.error('layout.js: add <aside class="sidebar" id="sidebar"></aside> to this page');
    return;
  }

  /* ---------- Menu configuration ----------
     url   = page_url stored in the backend "pages" table (from GET /pages/my-menu)
     file  = the HTML file in this frontend
     ready = false shows a greyed-out "Soon" link. Set to true when the page exists.
     The ORDER of this list is the order shown in the sidebar. */
  const MENU_ROUTES = [
    { url: "/maintenance", label: "Maintenance", file: "maintenance.html", icon: "maintenance", ready: false },
    { url: "/contact",     label: "Contact Us",  file: "contact.html",     icon: "contact",     ready: true  },
    { url: "/about",       label: "About Us",    file: "about.html",       icon: "about",       ready: true  },
  ];
  const PROFILE_FILE = "profile.html"; // opened from the user card, not the menu

  const ICONS = {
    plant: '<path d="M12 21v-8"/><path d="M12 13c0-4-3-6-7-6 0 4 3 6 7 6z"/><path d="M12 13c0-3 2-5 6-5 0 3-2 5-6 5z"/>',
    rent: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    buy: '<path d="M4 5h2l2 10h9l2-7H7"/><circle cx="10" cy="19" r="1.2"/><circle cx="17" cy="19" r="1.2"/>',
    maintenance: '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/>',
    contact: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    about: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    logout: '<path d="M10 4H5v16h5M15 8l4 4-4 4M19 12H9"/>',
  };
  const svg = (name) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;

  const currentFile = window.location.pathname.split("/").pop() || "index.html";

  /* ---------- 1. Render the sidebar skeleton immediately ----------
     Everything here is a fixed string, so innerHTML is safe.
     User-provided data is added later with textContent only.
     The ids (sidebarAvatar, sidebarName, sidebarRole, logoutBtn) are the
     same ones profile.html / app.js already expect. */
  sidebar.innerHTML = `
    <div class="brand">
      <svg class="logo" viewBox="0 0 24 24" aria-hidden="true">
        <rect width="24" height="24" rx="6" fill="#0f4d1f" />
        <path d="M6 18c0-8 5-12 12-12 0 8-4 12-12 12z" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round" />
        <path d="M6 18l7-7" stroke="#fff" stroke-width="1.6" stroke-linecap="round" />
      </svg>
      <span>Green Forest</span>
    </div>

    <a class="user-chip${currentFile === PROFILE_FILE ? " active" : ""}" href="${PROFILE_FILE}" title="View my profile">
      <div class="avatar" id="sidebarAvatar">?</div>
      <div>
        <div class="user-chip-name" id="sidebarName">Loading...</div>
        <div class="user-chip-role" id="sidebarRole">&nbsp;</div>
      </div>
    </a>

    <nav class="nav" id="sidebarNav" aria-label="Main menu">
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
    </nav>

    <button type="button" class="nav-link logout" id="logoutBtn">${svg("logout")}Logout</button>
  `;

  /* ---------- 2. Logout ----------
     profile.html's own code (app.js) already handles logout on that page,
     so we skip it there to avoid sending two logout requests. */
  if (body.dataset.page !== "profile") {
    document.getElementById("logoutBtn").addEventListener("click", async () => {
      try {
        await apiRequest("/auth/logout", { method: "POST", auth: true });
      } catch (err) {
        /* even if the request fails, still log out locally */
      }
      clearToken();
      window.location.href = "login.html";
    });
  }

  /* ---------- 3. Fill in the user card ---------- */
  function renderUser(user) {
    document.getElementById("sidebarAvatar").textContent = user.name.trim().charAt(0).toUpperCase();
    document.getElementById("sidebarName").textContent = user.name;
    document.getElementById("sidebarRole").textContent = user.role.role_name;
  }

  /* ---------- 4. Build the menu ----------
     allowedUrls = Set of page_url values from /pages/my-menu,
     or null if that request failed (then show the full default menu
     so the user is never stuck without navigation). */
  function renderNav(allowedUrls) {
    const nav = document.getElementById("sidebarNav");
    nav.replaceChildren();

    const items = MENU_ROUTES.filter((r) => !allowedUrls || allowedUrls.has(r.url));
    if (items.length === 0) {
      const note = document.createElement("div");
      note.className = "nav-note";
      note.textContent = "No menu items available for your account.";
      nav.append(note);
      return;
    }

    items.forEach((route) => {
      const isActive = route.file === currentFile;
      const node = document.createElement(route.ready ? "a" : "span");

      node.className = "nav-link" + (isActive ? " active" : "") + (route.ready ? "" : " disabled");
      if (route.ready) node.href = route.file;
      else node.setAttribute("aria-disabled", "true");
      if (isActive) node.setAttribute("aria-current", "page");

      node.innerHTML = svg(route.icon);
      node.append(document.createTextNode(route.label));

      if (!route.ready) {
        const tag = document.createElement("span");
        tag.className = "soon-tag";
        tag.textContent = "Soon";
        node.append(tag);
      }
      nav.append(node);
    });
  }

  /* ---------- 5. Load data from the backend ---------- */
  async function init() {
    const [me, menu] = await Promise.allSettled([
      apiRequest("/users/me", { auth: true }),
      apiRequest("/pages/my-menu", { auth: true }),
    ]);
    // (a 401 is handled inside apiRequest: token cleared, redirect to login)

    if (me.status === "fulfilled") renderUser(me.value);
    else document.getElementById("sidebarName").textContent = "My account";

    let allowedUrls = null;
    if (menu.status === "fulfilled") {
      allowedUrls = new Set(menu.value.map((page) => page.page_url));
    } else {
      console.warn("Could not load /pages/my-menu, showing the default menu:", menu.reason);
    }
    renderNav(allowedUrls);

    return { user: me.status === "fulfilled" ? me.value : null };
  }

  // Pages that need the current user can do:  const { user } = await dashboardShell.ready;
  window.dashboardShell = { ready: init() };
})();