/**
 * Injects a "Sign in to Surge POS" button on the Frappe /login page.
 *
 * Frappe can serve the login page at /login (direct) or /#login (desk SPA).
 * We detect by pathname OR hash OR body[data-path].
 *
 * Frappe v15 DOM structure (login.html):
 *   .login-content.page-card
 *     form.form-signin.form-login
 *       .page-card-body          ← inputs
 *       .page-card-actions       ← Login button
 *     .social-logins
 *       .login-with-email-link   ← "Login with Email Link" (only if enabled)
 *
 * Insert after .login-with-email-link → .social-logins → .page-card-actions.
 */
(function () {
  // TC6: already-authenticated pos-only user visits /login.
  // Ask surge.py whether this session has desk access. If not — redirect to /surge.
  // Uses a lightweight fetch so we don't block the page render.
  if (typeof frappe !== "undefined" && frappe.session && frappe.session.user !== "Guest") {
    fetch("/api/method/surge.utils.auth.get_session_user_flags", {
      credentials: "include",
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data) return;
        var flags = data.message || {};
        if (flags.has_pos && !flags.has_desk) {
          window.location.replace("/surge");
        }
      })
      .catch(function () { /* network error — do nothing */ });
  }

  function isLoginPage() {
    if (window.location.pathname.startsWith("/login")) return true;
    if (window.location.hash === "#login") return true;
    // Frappe sets data-path="login" on <body> for its desk SPA routes
    var bp = document.body && document.body.getAttribute("data-path");
    if (bp === "login") return true;
    return false;
  }

  if (!isLoginPage()) return;

  var INJECT_ID = "surge-pos-login-btn";

  function buildButton() {
    var wrapper = document.createElement("div");
    wrapper.id = INJECT_ID;
    wrapper.className = "login-button-wrapper";
    wrapper.style.marginTop = "8px";

    var divider = document.createElement("p");
    divider.className = "text-muted login-divider";
    divider.style.textAlign = "center";
    divider.textContent = "or";

    var link = document.createElement("a");
    link.href = "/surge";
    link.className = "btn btn-block btn-default btn-sm";
    link.style.cssText = "border-color:#6366f1;color:#6366f1;font-weight:500;";
    link.textContent = "Sign in to Surge POS";

    link.addEventListener("mouseenter", function () {
      link.style.background = "#6366f1";
      link.style.color = "#fff";
    });
    link.addEventListener("mouseleave", function () {
      link.style.background = "";
      link.style.color = "#6366f1";
    });

    wrapper.appendChild(divider);
    wrapper.appendChild(link);
    return wrapper;
  }

  function inject() {
    if (document.getElementById(INJECT_ID)) return false;

    // 1. After "Login with Email Link" block (only rendered if feature is on)
    var target = document.querySelector(".login-with-email-link");
    if (target) { target.after(buildButton()); return true; }

    // 2. Append inside .social-logins (holds "or" + email link + social)
    target = document.querySelector(".social-logins");
    if (target) { target.appendChild(buildButton()); return true; }

    // 3. After .page-card-actions (always present — holds Login button)
    target = document.querySelector(".page-card-actions");
    if (target) { target.after(buildButton()); return true; }

    return false;
  }

  // Frappe renders the login HTML synchronously — try immediately
  if (document.readyState !== "loading") {
    if (inject()) return;
  }

  // MutationObserver catches cases where the form renders after the script
  var observer = new MutationObserver(function () {
    if (inject()) observer.disconnect();
  });

  function startObserver() {
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(function () { observer.disconnect(); }, 15000);
  }

  if (document.body) {
    startObserver();
  } else {
    document.addEventListener("DOMContentLoaded", function () {
      if (!inject()) startObserver();
    });
  }
})();
