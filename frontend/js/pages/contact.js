/* Contact Us page: POST /contact  { name, email, subject, message }
   The endpoint is public, so no token is sent.
   Limits below match the backend schema (ContactCreate). */
   (function () {
    "use strict";
  
    const form = document.getElementById("contactForm");
    const button = document.getElementById("submitBtn");
    const nameInput = document.getElementById("name");
    const emailInput = document.getElementById("email");
    const subjectInput = document.getElementById("subject");
    const messageInput = document.getElementById("messageText");
    const charCount = document.getElementById("charCount");
  
    const MAX_MESSAGE = 2000;
  
    /* ---------- Character counter ---------- */
    function updateCount() {
      const length = messageInput.value.length;
      charCount.textContent = `${length} / ${MAX_MESSAGE}`;
      charCount.classList.toggle("limit", length >= MAX_MESSAGE);
    }
    messageInput.addEventListener("input", updateCount);
    updateCount();
  
    /* ---------- Prefill name / email from the logged-in user ---------- */
    if (window.dashboardShell) {
      window.dashboardShell.ready.then(({ user }) => {
        if (!user) return;
        if (!nameInput.value) nameInput.value = user.name;
        if (!emailInput.value) emailInput.value = user.email;
      });
    }
  
    /* ---------- Show the contact email from GET /about (optional) ---------- */
    async function loadContactEmail() {
      const link = document.getElementById("contactEmail");
      try {
        const about = await apiRequest("/about");
        if (isValidEmail(about.contact_email)) {
          link.href = `mailto:${about.contact_email}`;
          link.textContent = about.contact_email;
          return;
        }
      } catch (err) {
        /* not important: just hide the placeholder below */
      }
      link.textContent = "Use the form";
      link.removeAttribute("href");
    }
    loadContactEmail();
  
    /* ---------- Submit ---------- */
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      hideMessage();
  
      const name = nameInput.value.trim();
      const email = emailInput.value.trim();
      const subject = subjectInput.value.trim();
      const message = messageInput.value.trim();
  
      // Quick checks here; the backend validates everything again.
      if (name.length < 2) return showMessage("Please enter your name (at least 2 characters).");
      if (!isValidEmail(email)) return showMessage("Please enter a valid email address.");
      if (subject.length < 3) return showMessage("Please enter a subject (at least 3 characters).");
      if (message.length < 10) return showMessage("Your message must be at least 10 characters.");
      if (message.length > MAX_MESSAGE) return showMessage(`Your message must be at most ${MAX_MESSAGE} characters.`);
  
      setLoading(button, true, "Sending...");
      try {
        const data = await apiRequest("/contact", {
          method: "POST",
          body: { name, email, subject, message },
        });
        showMessage(data.message, "success");
  
        // Keep name and email, clear the rest so the form is ready for next time
        subjectInput.value = "";
        messageInput.value = "";
        updateCount();
      } catch (err) {
        showMessage(err.message);
      } finally {
        setLoading(button, false);
        document.getElementById("message").scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    });
  })();