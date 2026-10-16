/* =========================================================
   Shared dashboard layout: sidebar, menu, user card, logout.

   Used by every authenticated portal page that has:
     <body data-layout="dashboard"> or <body data-layout="nursery">

   and:

     <aside class="sidebar"></aside>

   SCRIPT ORDER:
     1. js/app.js
     2. js/layout.js
     3. page-specific JS
   ========================================================= */

(function () {
  "use strict";

  const body = document.body;

  const layoutRole =
    body.dataset.layout === "dashboard"
      ? "User"
      : body.dataset.layout === "nursery"
        ? "Nursery"
        : null;

  if (!layoutRole) {
    return;
  }

  /* ---------- Authentication ---------- */

  body.style.visibility = "hidden";

  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }

  const sidebar = document.querySelector(".sidebar");

  if (!sidebar) {
    console.error(
      "layout.js: add a sidebar element to this page"
    );
    body.style.visibility = "visible";
    return;
  }

  /* =========================================================
     Menu configuration
     ========================================================= */

  const MENU_ROUTES = {
    User: [
      {
        url: "/dashboard",
        label: "Dashboard",
        file: "dashboard.html",
        icon: "dashboard"
      },
      { url: "/buy", label: "Buy", file: "buy.html", icon: "buy" },
      { url: "/rent", label: "Rent", file: "rent.html", icon: "rent" },
      {
        url: "/customer-history",
        label: "Purchase History",
        file: "customer-history.html",
        icon: "orders"
      },
      {
        url: "/maintenance",
        label: "Maintenance",
        file: "maintenance.html",
        icon: "maintenance"
      },
      { url: "/profile", label: "Profile", file: "profile.html", icon: "profile" }
    ],
    Nursery: [
      {
        url: "/nursery-dashboard",
        label: "Nursery Dashboard",
        file: "nursery-dashboard.html",
        icon: "dashboard"
      },
      {
        url: "/my-plants",
        label: "My Plants",
        file: "my-plants.html",
        icon: "plants"
      },
      {
        url: "/add-plant",
        label: "Add Plant",
        file: "add-plant.html",
        icon: "add"
      },
      {
        url: "/sell-orders",
        label: "Sell Orders",
        file: "sell-orders.html",
        icon: "orders"
      },
      {
        url: "/rent-orders",
        label: "Rent Orders",
        file: "rent-orders.html",
        icon: "orders"
      },
      {
        url: "/nursery-maintenance",
        label: "Nursery Maintenance",
        file: "nursery-maintainance.html",
        icon: "maintenance"
      },
      {
        url: "/nursery-profile",
        label: "Nursery Profile",
        file: "nursery-profile.html",
        icon: "profile"
      }
    ]
  };

  /* =========================================================
     Icons
     ========================================================= */

  const ICONS = {
    dashboard:
      '<path d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"/>',

    buy:
      '<path d="M4 5h2l2 10h9l2-7H7"/>' +
      '<circle cx="10" cy="19" r="1.2"/>' +
      '<circle cx="17" cy="19" r="1.2"/>',

    rent:
      '<rect x="4" y="5" width="16" height="15" rx="2"/>' +
      '<path d="M4 10h16M9 3v4M15 3v4"/>',

    maintenance:
      '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/>',

    plants:
      '<path d="M20 4c-8 0-13 4-13 11 0 2 1 4 3 5 7 0 11-6 10-16z"/>' +
      '<path d="M4 21c3-5 6-8 11-11"/>',

    add: '<path d="M12 5v14M5 12h14"/>',

    orders:
      '<path d="M6 3h12v18H6zM9 7h6M9 11h6M9 15h4"/>',

    profile:
      '<circle cx="12" cy="9" r="3.5"/>' +
      '<path d="M5 20c1-4 4-5.5 7-5.5s6 1.5 7 5.5"/>',

    logout:
      '<path d="M10 4H5v16h5M15 8l4 4-4 4M19 12H9"/>'
  };

  const svg = (name) =>
    `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[name]}</svg>`;

  const currentFile =
    window.location.pathname.split("/").pop() ||
    "index.html";

  /* =========================================================
     1. Render sidebar skeleton
     ========================================================= */

  sidebar.innerHTML = `
    <div class="brand">
      <svg
        class="logo"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <rect
          width="24"
          height="24"
          rx="6"
          fill="#0f4d1f"
        />
        <path
          d="M6 18c0-8 5-12 12-12 0 8-4 12-12 12z"
          fill="none"
          stroke="#fff"
          stroke-width="1.6"
          stroke-linejoin="round"
        />
        <path
          d="M6 18l7-7"
          stroke="#fff"
          stroke-width="1.6"
          stroke-linecap="round"
        />
      </svg>
      <span>Green Forest</span>
    </div>

    <div class="user-chip">
      <div
        class="avatar"
        id="sidebarAvatar"
      >
        ?
      </div>
      <div>
        <div
          class="user-chip-name"
          id="sidebarName"
        >
          Loading...
        </div>
        <div
          class="user-chip-role"
          id="sidebarRole"
        >
          &nbsp;
        </div>
      </div>
    </div>

    <nav
      class="nav"
      id="sidebarNav"
      aria-label="Main menu"
    >
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
      <div class="nav-skeleton"></div>
    </nav>

    <button
      type="button"
      class="nav-link logout"
      id="logoutBtn"
    >
      ${svg("logout")}
      Logout
    </button>
  `;

  /* =========================================================
     2. Logout
     ========================================================= */

  if (body.dataset.page !== "profile") {
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
                auth: true
              }
            );
          } catch (err) {
            /* Still logout locally */
          }

          clearToken();

          window.location.href =
            "login.html";
        }
      );
  }

  /* =========================================================
     3. Profile image URL helper
     ========================================================= */

  function getImageUrl(profileImage) {
    if (!profileImage) {
      return null;
    }

    if (
      profileImage.startsWith("http://") ||
      profileImage.startsWith("https://")
    ) {
      return profileImage;
    }

    return `${API_ORIGIN}${profileImage}`;
  }

  /* =========================================================
     4. Fill user card
     ========================================================= */

  function renderUser(user) {
    const avatar =
      document.getElementById("sidebarAvatar");

    const initial =
      user.name
        .trim()
        .charAt(0)
        .toUpperCase();

    const imageUrl =
      getImageUrl(user.profile_image);

    if (imageUrl) {
      avatar.textContent = "";
      avatar.style.backgroundImage =
        `url("${imageUrl}")`;
      avatar.style.backgroundSize =
        "cover";
      avatar.style.backgroundPosition =
        "center";
      avatar.style.backgroundRepeat =
        "no-repeat";
    } else {
      avatar.style.backgroundImage =
        "none";
      avatar.textContent =
        initial;
    }

    document
      .getElementById("sidebarName")
      .textContent =
      user.name;

    document
      .getElementById("sidebarRole")
      .textContent =
      user.role.role_name;
  }

  /* =========================================================
     5. Build menu
     ========================================================= */

  function renderNav(role, allowedUrls) {
    const nav =
      document.getElementById(
        "sidebarNav"
      );

    nav.replaceChildren();

    const items = MENU_ROUTES[role].filter((route) =>
      allowedUrls.has(route.url)
    );

    if (items.length === 0) {
      const note =
        document.createElement("div");

      note.className =
        "nav-note";

      note.textContent =
        "No menu items available for your account.";

      nav.append(note);

      return;
    }

    items.forEach((route) => {
      const isActive =
        route.file === currentFile;

      const node = document.createElement("a");
      node.className = "nav-link" + (isActive ? " active" : "");
      node.href = route.file;

      if (isActive) {
        node.setAttribute(
          "aria-current",
          "page"
        );
      }

      node.innerHTML =
        svg(route.icon);

      node.append(
        document.createTextNode(
          route.label
        )
      );

      nav.append(node);
    });
  }

  /* =========================================================
     6. Load backend data
     ========================================================= */

  function showAuthorizationError(error) {
    console.error("Could not verify portal access:", error);
    document.querySelector(".app-layout").hidden = true;
    const message = document.createElement("p");
    message.className = "alert alert-error";
    message.textContent =
      "Your access could not be verified. Please try again when the service is available.";
    body.append(message);
    body.style.visibility = "visible";
  }

  async function init() {
    try {
      const user = await apiRequest("/users/me", { auth: true });
      const role = user.role && user.role.role_name;

      if (role !== layoutRole) {
        const portal = {
          User: "dashboard.html",
          Nursery: "nursery-dashboard.html"
        }[role];

        if (portal) {
          window.location.replace(portal);
        } else {
          clearToken();
          window.location.replace("login.html");
        }
        return { user: null };
      }

      const menu = await apiRequest("/pages/my-menu", { auth: true });
      renderUser(user);
      renderNav(
        role,
        new Set(menu.map((page) => page.page_url))
      );
      body.style.visibility = "visible";

      return { user };
    } catch (error) {
      showAuthorizationError(error);
      return { user: null };
    }
  }

  window.dashboardShell = {
    ready: init()
  };

})();