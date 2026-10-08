
/* =========================================================
   Shared dashboard layout: sidebar, menu, user card, logout.

   Used by every page that has:
     <body data-layout="dashboard">

   and:

     <aside class="sidebar" id="sidebar"></aside>

   SCRIPT ORDER:

     1. js/app.js
     2. js/layout.js
     3. page-specific JS
   ========================================================= */

(function () {
  "use strict";

  const body = document.body;

  if (body.dataset.layout !== "dashboard") {
    return;
  }


  /* ---------- Authentication ---------- */

  if (!getToken()) {
    window.location.replace("login.html");
    return;
  }


  const sidebar =
    document.getElementById("sidebar");

  if (!sidebar) {
    console.error(
      'layout.js: add <aside class="sidebar" id="sidebar"></aside> to this page'
    );
    return;
  }


  /* =========================================================
     Menu configuration
     ========================================================= */

  const MENU_ROUTES = [

    {
      url: "/plants",
      label: "Plants",
      file: "plants.html",
      icon: "plant",
      ready: true
    },

    {
      url: "/buy",
      label: "Buy",
      file: "buy.html",
      icon: "buy",
      ready: true
    },

    {
      url: "/rent",
      label: "Rent",
      file: "rent.html",
      icon: "rent",
      ready: true
    },

    {
      url: "/maintenance",
      label: "Maintenance",
      file: "maintenance.html",
      icon: "maintenance",
      ready: false
    },

    {
      url: "/about",
      label: "About Us",
      file: "about.html",
      icon: "about",
      ready: true
    },

    {
      url: "/contact",
      label: "Contact Us",
      file: "contact.html",
      icon: "contact",
      ready: true
    }
  ];


  const PROFILE_FILE =
    "profile.html";


  /* =========================================================
     Icons
     ========================================================= */

  const ICONS = {

    plant:
      '<path d="M12 21v-8"/>' +
      '<path d="M12 13c0-4-3-6-7-6 0 4 3 6 7 6z"/>' +
      '<path d="M12 13c0-3 2-5 6-5 0 3-2 5-6 5z"/>',

    rent:
      '<rect x="4" y="5" width="16" height="15" rx="2"/>' +
      '<path d="M4 10h16M9 3v4M15 3v4"/>',

    buy:
      '<path d="M4 5h2l2 10h9l2-7H7"/>' +
      '<circle cx="10" cy="19" r="1.2"/>' +
      '<circle cx="17" cy="19" r="1.2"/>',

    maintenance:
      '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z"/>',

    contact:
      '<rect x="3" y="5" width="18" height="14" rx="2"/>' +
      '<path d="M3 7l9 6 9-6"/>',

    about:
      '<circle cx="12" cy="12" r="9"/>' +
      '<path d="M12 11v5M12 8h.01"/>',

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


    <a
      class="user-chip${currentFile === PROFILE_FILE ? " active" : ""}"
      href="${PROFILE_FILE}"
      title="View my profile"
    >

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

    </a>


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

  function renderNav(allowedUrls) {

    const nav =
      document.getElementById(
        "sidebarNav"
      );

    nav.replaceChildren();


    const items =
      MENU_ROUTES.filter(
        (route) =>
          !allowedUrls ||
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


      const node =
        document.createElement(
          route.ready
            ? "a"
            : "span"
        );


      node.className =
        "nav-link" +
        (isActive
          ? " active"
          : "") +
        (route.ready
          ? ""
          : " disabled");


      if (route.ready) {
        node.href =
          route.file;
      } else {
        node.setAttribute(
          "aria-disabled",
          "true"
        );
      }


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


      if (!route.ready) {

        const tag =
          document.createElement(
            "span"
          );

        tag.className =
          "soon-tag";

        tag.textContent =
          "Soon";

        node.append(tag);
      }


      nav.append(node);
    });
  }


  /* =========================================================
     6. Load backend data
     ========================================================= */

  async function init() {

    const [me, menu] =
      await Promise.allSettled([

        apiRequest(
          "/users/me",
          { auth: true }
        ),

        apiRequest(
          "/pages/my-menu",
          { auth: true }
        )
      ]);


    /*
     * 401 is already handled by apiRequest().
     */

    if (me.status === "fulfilled") {

      renderUser(
        me.value
      );

    } else {

      document
        .getElementById(
          "sidebarName"
        )
        .textContent =
        "My account";
    }


    let allowedUrls = null;


    if (
      menu.status ===
      "fulfilled"
    ) {

      allowedUrls =
        new Set(
          menu.value.map(
            (page) =>
              page.page_url
          )
        );

    } else {

      console.warn(
        "Could not load /pages/my-menu, showing the default menu:",
        menu.reason
      );
    }


    renderNav(
      allowedUrls
    );


    return {
      user:
        me.status === "fulfilled"
          ? me.value
          : null
    };
  }


  /*
   * Pages that need current user:
   *
   * const { user } =
   *   await dashboardShell.ready;
   */

  window.dashboardShell = {
    ready: init()
  };

})();

