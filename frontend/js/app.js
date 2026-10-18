/* =========================================================
   Green Forest frontend: one file, shared by every page.
   Each page sets <body data-page="..."> and the matching
   function at the bottom runs for that page.
   ========================================================= */

// Backend API
const API_BASE = (
  window.GRENNEST_API_URL ||
  `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8000/api/v1`
).replace(/\/$/, "");
const TOKEN_KEY = "greennest_token";

// Full backend URL for uploaded files
const API_ORIGIN = new URL(API_BASE, window.location.href).origin;


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
   PAGE: public landing page
   ========================================================= */
function initLandingPage() {
  const grid = document.getElementById("landingPlantGrid");
  const modal = document.getElementById("landingAuthModal");
  const loginForm = document.getElementById("landingLoginForm");
  const registerForm = document.getElementById("landingRegisterForm");
  const contactForm = document.getElementById("landingContactForm");
  const message = document.getElementById("landingAuthMessage");
  const contactFeedback = document.getElementById("landingContactFeedback");
  const authTitle = document.getElementById("landingAuthTitle");
  const modalIntro = document.querySelector(".landing-modal-intro");
  const filterButtons = [...document.querySelectorAll(".landing-filter-tabs [data-catalog-mode]")];
  const views = [...document.querySelectorAll("[data-view]")];
  const menuToggle = document.querySelector(".landing-menu-toggle");
  const navigation = document.getElementById("landingNavigation");
  const fallbackImages = [
    "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1497250681960-ef046c08a56e?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1509423350716-97f9360b4e09?auto=format&fit=crop&w=700&q=80",
    "https://images.unsplash.com/photo-1485955900006-10f4d324d411?auto=format&fit=crop&w=700&q=80",
  ];
  let plants = [];
  let catalogMode = "all";
  let pendingAction = null;
  let previousFocus = null;

  document.getElementById("landingYear").textContent = new Date().getFullYear();

  const getViewFromHash = () => {
    const hash = window.location.hash.slice(1);
    const sectionToView = {
      categories: "home",
      sell: "home",
    };
    const requestedView = sectionToView[hash] || hash;
    return views.some((view) => view.dataset.view === requestedView)
      ? requestedView
      : "home";
  };

  const showView = (viewName, { updateHistory = true } = {}) => {
    const selectedView = views.find((view) => view.dataset.view === viewName);
    if (!selectedView) return;

    views.forEach((view) => {
      const isSelected = view === selectedView;
      view.hidden = !isSelected;
      view.setAttribute("aria-hidden", String(!isSelected));
    });
    if (updateHistory && window.location.hash !== `#${viewName}`) {
      window.history.pushState({ view: viewName }, "", `#${viewName}`);
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const showAuthMessage = (text, type = "error") => {
    message.textContent = text;
    message.classList.toggle("success", type === "success");
    message.hidden = false;
  };

  const clearAuthMessage = () => {
    message.textContent = "";
    message.classList.remove("success");
    message.hidden = true;
  };

  const setAuthMode = (mode) => {
    const registering = mode === "register";
    loginForm.hidden = registering;
    registerForm.hidden = !registering;
    authTitle.textContent = registering ? "Create your account" : "Welcome back";
    modalIntro.textContent = registering
      ? "Join a community that loves a little more green."
      : "Log in to continue with your plants.";
    clearAuthMessage();
  };

  const openAuthModal = (mode = "login", action = null) => {
    if (getToken()) {
      window.location.href = action === "rent"
        ? "rent.html"
        : action === "buy"
          ? "buy.html"
          : "profile.html";
      return;
    }
    pendingAction = action;
    setAuthMode(mode);
    previousFocus = document.activeElement;
    modal.hidden = false;
    document.body.classList.add("landing-modal-open");
    const firstInput = mode === "register"
      ? document.getElementById("landingRegisterName")
      : document.getElementById("landingLoginEmail");
    firstInput.focus();
  };

  const closeAuthModal = () => {
    modal.hidden = true;
    document.body.classList.remove("landing-modal-open");
    pendingAction = null;
    if (previousFocus && typeof previousFocus.focus === "function") {
      previousFocus.focus();
    }
  };

  const setCatalogMode = (mode) => {
    catalogMode = mode;
    filterButtons.forEach((button) => {
      const active = button.dataset.catalogMode === mode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    renderPlants();
  };

  const hasOption = (plant, mode) => {
    const status = plant.availability_status;
    const inStock = Number(plant.available_quantity) > 0;
    const canRent = ["available_for_rent", "available_for_both"].includes(status)
      && plant.rent_price !== null && plant.rent_price !== undefined;
    const canBuy = ["available_for_sale", "available_for_both"].includes(status)
      && plant.buy_price !== null && plant.buy_price !== undefined;
    if (!inStock) return false;
    if (mode === "rent") return canRent;
    if (mode === "sale") return canBuy;
    return canRent || canBuy;
  };

  const makePrice = (price, suffix) => {
    const wrapper = document.createElement("span");
    wrapper.append(document.createTextNode(suffix));
    const strong = document.createElement("strong");
    const amount = Number(price);
    strong.textContent = `$${Number.isFinite(amount) ? amount.toFixed(2) : "—"}`;
    if (suffix === "Rent") {
      const unit = document.createElement("small");
      unit.textContent = " / day";
      strong.append(unit);
    }
    wrapper.append(strong);
    return wrapper;
  };

  const makePlantCard = (plant, index) => {
    const canRent = hasOption(plant, "rent");
    const canBuy = hasOption(plant, "sale");
    const card = document.createElement("article");
    card.className = "landing-plant-card";

    const imageWrap = document.createElement("div");
    imageWrap.className = "landing-plant-image-wrap";
    const image = document.createElement("img");
    image.className = "landing-plant-image";
    image.alt = plant.name ? `${plant.name} plant` : "Green plant";
    image.loading = "lazy";
    image.src = fallbackImages[index % fallbackImages.length];
    if (plant.image_url) {
      try {
        const imageUrl = new URL(plant.image_url, API_ORIGIN);
        if (["http:", "https:"].includes(imageUrl.protocol)) {
          image.src = imageUrl.href;
        }
      } catch (error) {
        // Keep the bundled-in-page fallback image if a listing URL is malformed.
      }
    }
    image.addEventListener("error", () => {
      image.remove();
      imageWrap.classList.add("image-unavailable");
    }, { once: true });
    const tag = document.createElement("span");
    tag.className = "landing-plant-tag";
    tag.textContent = canRent && canBuy ? "Rent or buy" : canRent ? "For rent" : "For sale";
    imageWrap.append(image, tag);

    const info = document.createElement("div");
    info.className = "landing-plant-info";
    const category = document.createElement("p");
    category.className = "landing-plant-category";
    category.textContent = plant.category || "Plant";
    const name = document.createElement("h3");
    name.textContent = plant.name || "Green favorite";
    const nursery = document.createElement("p");
    nursery.className = "landing-plant-nursery";
    nursery.textContent = plant.nursery_name ? `From ${plant.nursery_name}` : "Ready for a new home";
    const prices = document.createElement("div");
    prices.className = "landing-plant-prices";
    if (canRent) prices.append(makePrice(plant.rent_price, "Rent"));
    if (canBuy) prices.append(makePrice(plant.buy_price, "Buy"));
    const actions = document.createElement("div");
    actions.className = "landing-plant-actions";
    if (canRent) {
      const rentButton = document.createElement("button");
      rentButton.className = "landing-plant-action";
      rentButton.type = "button";
      rentButton.dataset.protectedAction = "rent";
      rentButton.textContent = "Rent now";
      actions.append(rentButton);
    }
    if (canBuy) {
      const buyButton = document.createElement("button");
      buyButton.className = "landing-plant-action";
      buyButton.type = "button";
      buyButton.dataset.protectedAction = "buy";
      buyButton.textContent = "Buy now";
      actions.append(buyButton);
    }
    info.append(category, name, nursery, prices, actions);
    card.append(imageWrap, info);
    return card;
  };

  function renderPlants() {
    if (!grid) return;
    const visiblePlants = plants.filter((plant) => hasOption(plant, catalogMode));
    grid.replaceChildren();
    if (!visiblePlants.length) {
      const empty = document.createElement("p");
      empty.className = "landing-catalog-state";
      empty.textContent = plants.length
        ? "No plants match this option just yet. Try another category."
        : "There are no available plant listings right now. Please check back soon.";
      grid.append(empty);
      return;
    }
    visiblePlants.slice(0, 8).forEach((plant, index) => {
      grid.append(makePlantCard(plant, index));
    });
  }

  const showCatalogError = () => {
    grid.replaceChildren();
    const state = document.createElement("p");
    state.className = "landing-catalog-state landing-error";
    state.append(document.createTextNode("We couldn’t load plant listings. "));
    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "landing-catalog-retry";
    retry.textContent = "Try again";
    retry.addEventListener("click", loadPlants, { once: true });
    state.append(retry);
    grid.append(state);
  };

  async function loadPlants() {
    grid.setAttribute("aria-busy", "true");
    try {
      plants = await apiRequest("/plants/public?limit=100");
      if (!Array.isArray(plants)) {
        throw new Error("Unexpected plant catalog response");
      }
      renderPlants();
    } catch (error) {
      showCatalogError();
    } finally {
      grid.setAttribute("aria-busy", "false");
    }
  }

  document.querySelectorAll("[data-view-target]").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const viewName = link.dataset.viewTarget;
      if (link.dataset.catalogMode) {
        setCatalogMode(link.dataset.catalogMode);
      }
      showView(viewName);
      if (link.closest(".landing-navigation")) {
        navigation.classList.remove("open");
        menuToggle.setAttribute("aria-expanded", "false");
      }
    });
  });
  document.querySelectorAll(".landing-filter-tabs [data-catalog-mode]").forEach((control) => {
    control.addEventListener("click", () => {
      setCatalogMode(control.dataset.catalogMode);
    });
  });
  window.addEventListener("popstate", () => {
    showView(getViewFromHash(), { updateHistory: false });
  });
  grid.addEventListener("click", (event) => {
    const button = event.target.closest("[data-protected-action]");
    const action = button?.dataset.protectedAction;
    if (action && ["rent", "buy", "checkout", "book"].includes(action)) {
      openAuthModal("login", action);
    }
  });
  document.querySelector(".landing-modal-close").addEventListener("click", closeAuthModal);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeAuthModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeAuthModal();
  });
  document.querySelectorAll("[data-auth-switch]").forEach((button) => {
    button.addEventListener("click", () => setAuthMode(button.dataset.authSwitch));
  });
  menuToggle.addEventListener("click", () => {
    const expanded = menuToggle.getAttribute("aria-expanded") === "true";
    menuToggle.setAttribute("aria-expanded", String(!expanded));
    navigation.classList.toggle("open", !expanded);
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAuthMessage();
    const email = document.getElementById("landingLoginEmail").value.trim();
    const password = document.getElementById("landingLoginPassword").value;
    if (!isValidEmail(email)) return showAuthMessage("Please enter a valid email address.");
    if (!password) return showAuthMessage("Please enter your password.");
    const button = loginForm.querySelector('[type="submit"]');
    setLoading(button, true, "Logging in…");
    try {
      const data = await apiRequest("/auth/login", { method: "POST", body: { email, password } });
      setToken(data.access_token);
      window.location.href = pendingAction === "rent"
        ? "rent.html"
        : pendingAction === "buy"
          ? "buy.html"
          : "profile.html";
    } catch (error) {
      showAuthMessage(error.message);
      setLoading(button, false);
    }
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearAuthMessage();
    const name = document.getElementById("landingRegisterName").value.trim();
    const email = document.getElementById("landingRegisterEmail").value.trim();
    const role = document.getElementById("landingRegisterRole").value;
    const password = document.getElementById("landingRegisterPassword").value;
    const confirmPassword = document.getElementById("landingRegisterConfirm").value;
    if (name.length < 2) return showAuthMessage("Name must be at least 2 characters.");
    if (!isValidEmail(email)) return showAuthMessage("Please enter a valid email address.");
    if (password.length < 8 || !/[A-Z]/.test(password) || !/[a-z]/.test(password) || !/[0-9]/.test(password)) {
      return showAuthMessage("Use at least 8 characters, including uppercase and lowercase letters and a number.");
    }
    if (password !== confirmPassword) return showAuthMessage("Passwords do not match.");
    const button = registerForm.querySelector('[type="submit"]');
    setLoading(button, true, "Creating account…");
    try {
      await apiRequest("/auth/register", {
        method: "POST",
        body: { name, email, password, role },
      });
      document.getElementById("landingLoginEmail").value = email;
      setAuthMode("login");
      showAuthMessage("Account created. Log in to continue.", "success");
    } catch (error) {
      showAuthMessage(error.message);
    } finally {
      setLoading(button, false);
    }
  });

  contactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    contactFeedback.hidden = true;
    contactFeedback.classList.remove("success");

    const name = document.getElementById("landingContactName").value.trim();
    const email = document.getElementById("landingContactEmail").value.trim();
    const subject = document.getElementById("landingContactSubject").value.trim();
    const contactMessage = document.getElementById("landingContactMessage").value.trim();

    if (name.length < 2) return showContactFeedback("Please enter your name (at least 2 characters).");
    if (!isValidEmail(email)) return showContactFeedback("Please enter a valid email address.");
    if (subject.length < 3) return showContactFeedback("Please enter a subject (at least 3 characters).");
    if (contactMessage.length < 10) return showContactFeedback("Your message must be at least 10 characters.");

    const button = contactForm.querySelector('[type="submit"]');
    setLoading(button, true, "Sending…");
    try {
      const result = await apiRequest("/contact", {
        method: "POST",
        body: { name, email, subject, message: contactMessage },
      });
      showContactFeedback(result.message || "Thank you! We have received your message.", "success");
      document.getElementById("landingContactSubject").value = "";
      document.getElementById("landingContactMessage").value = "";
    } catch (error) {
      showContactFeedback(error.message);
    } finally {
      setLoading(button, false);
    }
  });

  function showContactFeedback(text, type = "error") {
    contactFeedback.textContent = text;
    contactFeedback.classList.toggle("success", type === "success");
    contactFeedback.hidden = false;
  }

  showView(getViewFromHash(), { updateHistory: false });
  loadPlants();
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

    if (page === "landing") {
      initLandingPage();
    } else if (page === "index") {
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