/**
 * ResearchOS Client Enhancements
 * Static layout, keyboard shortcuts, and instant copy-to-clipboard.
 * No delayed DOM mutations or layout-shifting timeouts.
 */
function enhanceResearchOS() {
  // 1. Keyboard Shortcut: Ctrl+Enter / Cmd+Enter to generate article
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "enter") {
      const generateBtn =
        document.querySelector("#generate-btn button") ||
        document.querySelector("button#generate-btn");
      if (generateBtn && !generateBtn.disabled) {
        event.preventDefault();
        generateBtn.click();
      }
    }
  });

  // 2. Copy Article to Clipboard
  document.addEventListener("click", (event) => {
    const copyBtn = event.target.closest("#copy-btn");
    if (!copyBtn) return;

    const outputElem = document.querySelector("#article-output");
    if (!outputElem) return;

    const textToCopy = outputElem.innerText || outputElem.textContent || "";
    if (!textToCopy.trim()) return;

    navigator.clipboard.writeText(textToCopy).then(() => {
      const originalText = copyBtn.innerText;
      copyBtn.innerText = "✓  Copied!";
      copyBtn.style.borderColor = "#10b981";
      copyBtn.style.color = "#34d399";

      setTimeout(() => {
        copyBtn.innerText = originalText;
        copyBtn.style.borderColor = "";
        copyBtn.style.color = "";
      }, 2000);
    }).catch((err) => {
      console.warn("Clipboard copy failed:", err);
    });
  });

  // 3. New Research: Smoothly focus topic input
  document.addEventListener("click", (event) => {
    const newBtn = event.target.closest("#new-research-btn");
    if (!newBtn) return;

    requestAnimationFrame(() => {
      const textarea = document.querySelector("#topic-input textarea");
      if (textarea) {
        textarea.focus();
      }
    });
  });

  // 4. Mobile Drawer Hamburger Menu Controller
  function initMobileDrawer() {
    let backdrop = document.querySelector("#drawer-backdrop");
    if (!backdrop) {
      backdrop = document.createElement("div");
      backdrop.id = "drawer-backdrop";
      document.body.appendChild(backdrop);
    }

    function openDrawer() {
      const sidebar = document.querySelector("#sidebar");
      const menuBtn = document.querySelector("#mobile-menu-btn");
      if (sidebar) sidebar.classList.add("drawer-open");
      if (menuBtn) {
        menuBtn.classList.add("is-active");
        menuBtn.setAttribute("aria-expanded", "true");
      }
      document.body.classList.add("menu-open");
    }

    function closeDrawer() {
      const sidebar = document.querySelector("#sidebar");
      const menuBtn = document.querySelector("#mobile-menu-btn");
      if (sidebar) sidebar.classList.remove("drawer-open");
      if (menuBtn) {
        menuBtn.classList.remove("is-active");
        menuBtn.setAttribute("aria-expanded", "false");
      }
      document.body.classList.remove("menu-open");
    }

    function toggleDrawer() {
      const sidebar = document.querySelector("#sidebar");
      if (sidebar && sidebar.classList.contains("drawer-open")) {
        closeDrawer();
      } else {
        openDrawer();
      }
    }

    // Toggle on hamburger click
    document.addEventListener("click", (e) => {
      const menuBtn = e.target.closest("#mobile-menu-btn");
      if (menuBtn) {
        e.preventDefault();
        toggleDrawer();
        return;
      }

      // Close on drawer close button click
      const closeBtn = e.target.closest("#close-drawer-btn");
      if (closeBtn) {
        e.preventDefault();
        closeDrawer();
        return;
      }

      // Close on backdrop click
      if (e.target.id === "drawer-backdrop" || e.target.closest("#drawer-backdrop")) {
        e.preventDefault();
        closeDrawer();
        return;
      }

      // Auto-close drawer on mobile when user selects a history item
      if (window.innerWidth <= 768) {
        const historyItem = e.target.closest("#history-list label");
        if (historyItem) {
          setTimeout(closeDrawer, 180);
          return;
        }

        const newBtn = e.target.closest("#new-research-btn");
        if (newBtn) {
          setTimeout(closeDrawer, 120);
          return;
        }
      }
    });

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.body.classList.contains("menu-open")) {
        closeDrawer();
      }
    });

    // Close if resized to desktop width
    window.addEventListener("resize", () => {
      if (window.innerWidth > 768 && document.body.classList.contains("menu-open")) {
        closeDrawer();
      }
    });
  }

  initMobileDrawer();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", enhanceResearchOS);
} else {
  enhanceResearchOS();
}
