/**
 * ResearchOS Client Enhancements
 * - Auto-disable Generate button when topic input is empty
 * - Auto-scroll down to loading area on generate
 * - Unselect history on "New Research"
 * - Dynamic high-end multi-stage AI research loader with live elapsed timer
 * - Keyboard shortcuts, instant copy-to-clipboard, and mobile drawer
 */

function enhanceResearchOS() {
  if (window.__researchOSEnhanced) return;
  window.__researchOSEnhanced = true;

  let researchTimerInterval = null;
  let elapsedSeconds = 0;
  let isGenerating = false;
  let generationStartTime = 0;
  let generationBaselineText = "";
  let outputObserver = null;
  let historyObserver = null;
  let isEnhancingHistory = false;
  let historyDebounceTimeout = null;

  // ==========================================
  // 1. Topic Input & Generate Button Controller
  // ==========================================
  function updateGenerateBtnState() {
    const textarea = document.querySelector("#topic-input textarea");
    const generateBtn =
      document.querySelector("#generate-btn button") ||
      document.querySelector("button#generate-btn") ||
      document.querySelector("#generate-btn");

    if (!generateBtn) return;
    const btn = generateBtn.tagName === "BUTTON" ? generateBtn : generateBtn.querySelector("button") || generateBtn;

    const isEmpty = !textarea || !textarea.value || !textarea.value.trim();

    if (isEmpty) {
      btn.disabled = true;
      btn.setAttribute("disabled", "true");
      btn.setAttribute("aria-disabled", "true");
      generateBtn.classList.add("disabled");
      btn.classList.add("disabled");
    } else {
      btn.disabled = false;
      btn.removeAttribute("disabled");
      btn.removeAttribute("aria-disabled");
      generateBtn.classList.remove("disabled");
      btn.classList.remove("disabled");
    }
  }

  // Intercept topic input events instantly
  document.addEventListener("input", (e) => {
    if (e.target.closest("#topic-input")) {
      updateGenerateBtnState();
    }
  });

  document.addEventListener("change", (e) => {
    if (e.target.closest("#topic-input")) {
      updateGenerateBtnState();
    }
  });

  document.addEventListener("keyup", (e) => {
    if (e.target.closest("#topic-input")) {
      updateGenerateBtnState();
    }
  });

  // Intercept generate clicks in capture phase if empty, or start loader & scroll
  document.addEventListener(
    "click",
    (e) => {
      const genBtn = e.target.closest("#generate-btn");
      if (!genBtn) return;

      const textarea = document.querySelector("#topic-input textarea");
      const isEmpty = !textarea || !textarea.value || !textarea.value.trim();

      if (isEmpty) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        updateGenerateBtnState();
        if (textarea) {
          textarea.focus();
          textarea.style.borderColor = "#f87171";
          setTimeout(() => {
            textarea.style.borderColor = "";
          }, 1500);
        }
        return;
      }

      // Valid generation triggered: activate loader and scroll down immediately
      startResearchLoader();
      scrollToLoadingArea();
    },
    true
  );

  // Keyboard Shortcut: Ctrl+Enter / Cmd+Enter to generate article
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "enter") {
      const textarea = document.querySelector("#topic-input textarea");
      if (!textarea || !textarea.value.trim()) {
        event.preventDefault();
        if (textarea) textarea.focus();
        return;
      }

      const generateBtn =
        document.querySelector("#generate-btn button") ||
        document.querySelector("button#generate-btn");
      if (generateBtn && !generateBtn.disabled && !generateBtn.classList.contains("disabled")) {
        event.preventDefault();
        generateBtn.click();
      }
    }
  });

  // ==========================================
  // 2. Smooth Auto-Scroll to Loading Area
  // ==========================================
  function scrollToLoadingArea() {
    const target =
      document.querySelector("#research-loader") ||
      document.querySelector("#article-section");

    if (!target) return;

    const doScroll = () => {
      const workspace = document.querySelector("#workspace");
      if (workspace && workspace.scrollHeight > workspace.clientHeight) {
        const targetRect = target.getBoundingClientRect();
        const wsRect = workspace.getBoundingClientRect();
        // Position top of loader comfortably beneath sticky topbar
        const targetTop = workspace.scrollTop + (targetRect.top - wsRect.top) - 12;
        workspace.scrollTo({
          top: Math.max(0, targetTop),
          behavior: "smooth",
        });
      } else {
        const targetRect = target.getBoundingClientRect();
        const pageTop = window.pageYOffset || document.documentElement.scrollTop || 0;
        const targetTop = pageTop + targetRect.top - 16;
        window.scrollTo({
          top: Math.max(0, targetTop),
          behavior: "smooth",
        });
      }
    };

    doScroll();
    requestAnimationFrame(() => {
      setTimeout(doScroll, 80);
      setTimeout(doScroll, 220);
    });
  }

  // ==========================================
  // 3. Dynamic Multi-Stage AI Research Loader
  // ==========================================
  function setStageStatus(stageNum, state, statusText) {
    const stageEl = document.querySelector(`#stage-${stageNum}`);
    if (!stageEl) return;

    stageEl.classList.remove("active", "completed");
    if (state === "active") stageEl.classList.add("active");
    if (state === "completed") stageEl.classList.add("completed");

    const tagEl = stageEl.querySelector(".stage-status-tag");
    if (tagEl && statusText) {
      tagEl.textContent = statusText;
    }
  }

  function startResearchLoader() {
    isGenerating = true;
    generationStartTime = Date.now();

    const loader = document.querySelector("#research-loader");
    const output = document.querySelector("#article-output");
    if (output) {
      generationBaselineText = (output.innerText || output.textContent || "").trim();
      output.style.display = "none";
    }
    if (loader) {
      loader.style.display = "flex";
    }

    elapsedSeconds = 0;
    const timerText = document.querySelector("#loader-timer-text");
    if (timerText) timerText.textContent = "00:00";

    // Initialize stage 1
    setStageStatus(1, "active", "Searching web…");
    setStageStatus(2, "pending", "Pending");
    setStageStatus(3, "pending", "Pending");
    setStageStatus(4, "pending", "Pending");

    if (researchTimerInterval) clearInterval(researchTimerInterval);

    researchTimerInterval = setInterval(() => {
      elapsedSeconds++;
      const mins = String(Math.floor(elapsedSeconds / 60)).padStart(2, "0");
      const secs = String(elapsedSeconds % 60).padStart(2, "0");
      if (timerText) timerText.textContent = `${mins}:${secs}`;

      // Dynamic Stage Advancements calibrated to real Groq inference speed:
      if (elapsedSeconds <= 4) {
        setStageStatus(1, "active", "Searching web…");
      } else if (elapsedSeconds <= 9) {
        setStageStatus(1, "completed", "Done ✓");
        setStageStatus(2, "active", "Analyzing…");
      } else if (elapsedSeconds <= 16) {
        setStageStatus(1, "completed", "Done ✓");
        setStageStatus(2, "completed", "Done ✓");
        setStageStatus(3, "active", "Drafting…");
      } else {
        setStageStatus(1, "completed", "Done ✓");
        setStageStatus(2, "completed", "Done ✓");
        setStageStatus(3, "completed", "Done ✓");
        setStageStatus(4, "active", "Final Polish…");
      }
    }, 1000);
  }

  let hasTransitionedToOutput = false;
  let typingTimeout = null;

  function scrollFollowTyping() {
    const workspace = document.querySelector("#workspace");
    if (workspace && workspace.scrollHeight > workspace.clientHeight) {
      const distanceFromBottom = workspace.scrollHeight - workspace.scrollTop - workspace.clientHeight;
      if (distanceFromBottom < 300) {
        workspace.scrollTo({
          top: workspace.scrollHeight,
          behavior: "smooth",
        });
      }
    }
  }

  function completeAndStopLoader() {
    if (researchTimerInterval) {
      clearInterval(researchTimerInterval);
      researchTimerInterval = null;
    }

    // Mark ALL 4 stages completed with emerald checkmarks
    setStageStatus(1, "completed", "Done ✓");
    setStageStatus(2, "completed", "Done ✓");
    setStageStatus(3, "completed", "Done ✓");
    setStageStatus(4, "completed", "Done ✓");

    const loader = document.querySelector("#research-loader");
    const output = document.querySelector("#article-output");
    if (loader) loader.style.display = "none";
    if (output) {
      output.style.display = "block";
      output.classList.add("typing-active");
    }
  }

  function immediateStopLoader() {
    if (researchTimerInterval) {
      clearInterval(researchTimerInterval);
      researchTimerInterval = null;
    }
    isGenerating = false;
    hasTransitionedToOutput = false;
    generationStartTime = 0;
    generationBaselineText = "";

    if (typingTimeout) {
      clearTimeout(typingTimeout);
      typingTimeout = null;
    }

    const loader = document.querySelector("#research-loader");
    const output = document.querySelector("#article-output");
    if (loader) loader.style.display = "none";
    if (output) {
      output.style.display = "block";
      output.classList.remove("typing-active");
    }
  }

  // Observe article output to know when research finishes and animate text generation
  function initOutputObserver() {
    if (outputObserver) return;
    const output = document.querySelector("#article-output");
    if (!output) return;

    outputObserver = new MutationObserver(() => {
      if (!isGenerating) return;

      const currentText = (output.innerText || output.textContent || "").trim();

      // Guard: never stop within the first 2.5 seconds of generation
      if (Date.now() - generationStartTime < 2500) {
        return;
      }

      // If the text is still the intermediate loading yield
      const isConducting =
        currentText.includes("Conducting research") ||
        currentText.includes("Searching live web") ||
        currentText.includes("Preparing research");
      if (isConducting) {
        return;
      }

      // If the text is still the previous baseline before generation started
      if (currentText === generationBaselineText) {
        return;
      }

      // Once the real synthesized article content starts streaming in:
      if (currentText.length > 25) {
        if (!hasTransitionedToOutput) {
          hasTransitionedToOutput = true;
          completeAndStopLoader();
        }

        // Keep typing cursor active
        output.classList.add("typing-active");
        scrollFollowTyping();

        // When streaming ceases for 800ms, finalize and remove typing cursor
        if (typingTimeout) clearTimeout(typingTimeout);
        typingTimeout = setTimeout(() => {
          output.classList.remove("typing-active");
          isGenerating = false;
          hasTransitionedToOutput = false;
          generationStartTime = 0;
          generationBaselineText = "";
        }, 800);
      }
    });

    outputObserver.observe(output, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  // ==========================================
  // 4. New Research Button: Unselect History & Reset
  // ==========================================
  document.addEventListener("click", (event) => {
    const newBtn = event.target.closest("#new-research-btn");
    if (!newBtn) return;

    // 1. Immediately uncheck all radio buttons in client DOM
    const radios = document.querySelectorAll('#history-list input[type="radio"]');
    radios.forEach((r) => {
      r.checked = false;
    });

    // 2. Remove any active/selected classes on history items
    const activeLabels = document.querySelectorAll("#history-list label");
    activeLabels.forEach((label) => {
      label.classList.remove("selected");
    });

    // 3. Dismiss any active loader
    immediateStopLoader();

    // 4. Clear topic input and update disabled state
    requestAnimationFrame(() => {
      const textarea = document.querySelector("#topic-input textarea");
      if (textarea) {
        textarea.value = "";
        textarea.focus();
      }
      updateGenerateBtnState();
    });

    // Run update again after backend round-trip completes
    setTimeout(updateGenerateBtnState, 150);
  });

  // Clicking any history item stops any active loader
  document.addEventListener("click", (event) => {
    const historyItem = event.target.closest("#history-list label");
    if (historyItem) {
      immediateStopLoader();
    }
  });

  // ==========================================
  // 5. Copy Article to Clipboard
  // ==========================================
  document.addEventListener("click", (event) => {
    const copyBtn = event.target.closest("#copy-btn");
    if (!copyBtn) return;

    const outputElem = document.querySelector("#article-output");
    if (!outputElem) return;

    const textToCopy = outputElem.innerText || outputElem.textContent || "";
    if (!textToCopy.trim()) return;

    navigator.clipboard
      .writeText(textToCopy)
      .then(() => {
        const originalText = copyBtn.innerText;
        copyBtn.innerText = "✓  Copied!";
        copyBtn.style.borderColor = "#10b981";
        copyBtn.style.color = "#34d399";

        setTimeout(() => {
          copyBtn.innerText = originalText;
          copyBtn.style.borderColor = "";
          copyBtn.style.color = "";
        }, 2000);
      })
      .catch((err) => {
        console.warn("Clipboard copy failed:", err);
      });
  });

  // ==========================================
  // 6. Mobile Drawer Hamburger Menu Controller
  // ==========================================
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

    document.addEventListener("click", (e) => {
      const menuBtn = e.target.closest("#mobile-menu-btn");
      if (menuBtn) {
        e.preventDefault();
        toggleDrawer();
        return;
      }

      const closeBtn = e.target.closest("#close-drawer-btn");
      if (closeBtn) {
        e.preventDefault();
        closeDrawer();
        return;
      }

      if (e.target.id === "drawer-backdrop" || e.target.closest("#drawer-backdrop")) {
        e.preventDefault();
        closeDrawer();
        return;
      }

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

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && document.body.classList.contains("menu-open")) {
        closeDrawer();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 768 && document.body.classList.contains("menu-open")) {
        closeDrawer();
      }
    });
  }

  // ==========================================
  // 7. Individual History Deletion & Label Enhancer
  // ==========================================
  function enhanceHistoryList() {
    if (isEnhancingHistory) return;
    isEnhancingHistory = true;

    // Disconnect observer before making DOM modifications to prevent any feedback loops
    if (historyObserver) {
      historyObserver.disconnect();
    }

    try {
      const historyList = document.querySelector("#history-list");
      if (!historyList) return;

      const labels = historyList.querySelectorAll(
        ".wrap label, label[data-testid*='radio-label'], fieldset label, label.svelte-19qdtil"
      );

      labels.forEach((label) => {
        const radioInput = label.querySelector("input[type='radio']");
        const span = label.querySelector("span:not(.history-item-body span)");

        if (!span && !radioInput) return;

        // Extract raw text and keep Gradio's raw unstyled span completely hidden
        let rawText = "";
        if (span) {
          rawText = (span.textContent || "").trim();
          if (span.style.display !== "none") {
            span.style.setProperty("display", "none", "important");
          }
        }

        const articleId = radioInput ? radioInput.value : "";

        let titleText = "Untitled Research";
        let dateText = "";
        if (rawText) {
          const parts = rawText.split("\n");
          if (parts.length > 1) {
            dateText = parts[parts.length - 1].trim();
            titleText = parts.slice(0, parts.length - 1).join(" ").trim();
          } else {
            titleText = parts[0].trim();
          }
        }

        // Check if label already has structured container
        let bodyDiv = label.querySelector(".history-item-body");
        let delBtn = label.querySelector(".history-item-delete");

        if (bodyDiv) {
          const titleDiv = bodyDiv.querySelector(".history-item-title");
          const dateDiv = bodyDiv.querySelector(".history-item-date");

          if (titleDiv && titleText && titleDiv.textContent !== titleText) {
            titleDiv.textContent = titleText;
            titleDiv.title = titleText;
          }

          if (dateDiv) {
            if (dateText && dateDiv.textContent !== dateText) {
              dateDiv.textContent = dateText;
            }
            const expectedDisplay = dateText ? "" : "none";
            if (dateDiv.style.display !== expectedDisplay) {
              dateDiv.style.display = expectedDisplay;
            }
          } else if (dateText) {
            const newDateDiv = document.createElement("div");
            newDateDiv.className = "history-item-date";
            newDateDiv.textContent = dateText;
            bodyDiv.appendChild(newDateDiv);
          }
        } else {
          // Create new structured text container
          bodyDiv = document.createElement("div");
          bodyDiv.className = "history-item-body";

          const titleDiv = document.createElement("div");
          titleDiv.className = "history-item-title";
          titleDiv.textContent = titleText;
          titleDiv.title = titleText;
          bodyDiv.appendChild(titleDiv);

          if (dateText) {
            const dateDiv = document.createElement("div");
            dateDiv.className = "history-item-date";
            dateDiv.textContent = dateText;
            bodyDiv.appendChild(dateDiv);
          }

          label.appendChild(bodyDiv);
        }

        // Update or create delete button
        if (delBtn) {
          if (delBtn.getAttribute("data-id") !== articleId) {
            delBtn.setAttribute("data-id", articleId);
          }
          const ariaLabel = `Delete research ${titleText}`;
          if (delBtn.getAttribute("aria-label") !== ariaLabel) {
            delBtn.setAttribute("aria-label", ariaLabel);
          }
        } else {
          delBtn = document.createElement("button");
          delBtn.type = "button";
          delBtn.className = "history-item-delete";
          delBtn.setAttribute("data-id", articleId);
          delBtn.title = "Delete this research";
          delBtn.setAttribute("aria-label", `Delete research ${titleText}`);
          delBtn.innerHTML = `
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              <line x1="10" y1="11" x2="10" y2="17"></line>
              <line x1="14" y1="11" x2="14" y2="17"></line>
            </svg>
          `;
          label.appendChild(delBtn);
        }

        // Synchronize selection state
        if (radioInput && radioInput.checked) {
          if (!label.classList.contains("selected")) label.classList.add("selected");
        } else {
          if (label.classList.contains("selected")) label.classList.remove("selected");
        }
      });
    } finally {
      // Safely re-attach observer after DOM mutations are finalized
      const historyList = document.querySelector("#history-list");
      if (historyObserver && historyList) {
        historyObserver.observe(historyList, {
          childList: true,
          subtree: true,
        });
      }
      setTimeout(() => {
        isEnhancingHistory = false;
      }, 60);
    }
  }

  // Intercept per-item delete button clicks in capture phase
  document.addEventListener(
    "click",
    async (e) => {
      const delBtn = e.target.closest(".history-item-delete");
      if (!delBtn) return;

      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();

      const articleId = delBtn.getAttribute("data-id");
      if (!articleId) return;

      const label = delBtn.closest("label");
      const isCurrentlyActive =
        label && (label.classList.contains("selected") || label.querySelector("input:checked"));

      if (label) {
        label.style.opacity = "0.2";
        label.style.pointerEvents = "none";
        label.style.transform = "scale(0.96)";
      }

      try {
        const response = await fetch(`/api/articles/${encodeURIComponent(articleId)}/delete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });

        if (response.ok) {
          const data = await response.json();
          // Update metric counter in UI immediately
          const metricVal = document.querySelector(".metric-value");
          if (metricVal && data.count !== undefined) {
            metricVal.textContent = data.count;
          }

          // Trigger Gradio's official refresh to sync components
          const refreshBtn =
            document.querySelector("#refresh-history-btn button") ||
            document.querySelector("button#refresh-history-btn") ||
            document.querySelector("#refresh-history-btn");
          if (refreshBtn) {
            refreshBtn.click();
          }

          // If the deleted article was currently active, reset output
          if (isCurrentlyActive) {
            const newBtn =
              document.querySelector("#new-research-btn button") ||
              document.querySelector("button#new-research-btn") ||
              document.querySelector("#new-research-btn");
            if (newBtn) {
              setTimeout(() => newBtn.click(), 50);
            }
          }
        } else {
          console.error("Delete request failed:", response.status);
          if (label) {
            label.style.opacity = "";
            label.style.pointerEvents = "";
            label.style.transform = "";
          }
        }
      } catch (err) {
        console.error("Error executing delete:", err);
        if (label) {
          label.style.opacity = "";
          label.style.pointerEvents = "";
          label.style.transform = "";
        }
      }
    },
    true
  );

  // Clear all history confirmation dialog
  document.addEventListener(
    "click",
    (e) => {
      const clearBtn = e.target.closest("#clear-all-history-btn");
      if (!clearBtn) return;

      const confirmed = window.confirm("Are you sure you want to delete all research history? This cannot be undone.");
      if (!confirmed) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
      }
    },
    true
  );

  // Observe history list mutations to re-enhance items when list changes
  function initHistoryObserver() {
    if (historyObserver) return;
    const historyList = document.querySelector("#history-list");
    if (!historyList) return;

    historyObserver = new MutationObserver(() => {
      if (isEnhancingHistory) return;
      if (historyDebounceTimeout) clearTimeout(historyDebounceTimeout);
      historyDebounceTimeout = setTimeout(() => {
        enhanceHistoryList();
      }, 60);
    });

    historyObserver.observe(historyList, {
      childList: true,
      subtree: true,
    });
  }

  // Initialize
  initMobileDrawer();
  initOutputObserver();
  initHistoryObserver();
  enhanceHistoryList();
  updateGenerateBtnState();

  // Polling check on load to ensure sync with Gradio hydration
  let initAttempts = 0;
  const syncInterval = setInterval(() => {
    updateGenerateBtnState();
    initOutputObserver();
    initHistoryObserver();
    enhanceHistoryList();
    initAttempts++;
    if (initAttempts >= 10) clearInterval(syncInterval);
  }, 300);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", enhanceResearchOS);
} else {
  enhanceResearchOS();
}
