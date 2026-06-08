(function () {
  var root = document.querySelector("[data-dff-visual-root]");
  if (!root) {
    return;
  }

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.classList.add("dff-js-ready");

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function numberFromText(text) {
    var value = parseInt(String(text).replace(/[^\d-]/g, ""), 10);
    return Number.isFinite(value) ? value : 0;
  }

  function addMetricVisual(card, index) {
    if (card.querySelector(".dff-metric-visual")) {
      return;
    }

    var valueNode = card.querySelector("[data-dff-metric-value]");
    var value = valueNode ? numberFromText(valueNode.textContent) : 0;
    var nodeCount = clamp(value + 4, 4, 18);
    var visual = document.createElement("span");
    visual.className = "dff-metric-visual";
    visual.setAttribute("aria-hidden", "true");

    for (var i = 0; i < nodeCount; i += 1) {
      var node = document.createElement("span");
      var x = (17 + i * 29 + index * 13) % 92;
      var y = (21 + i * 37 + index * 19) % 82;
      node.style.setProperty("--dff-node-x", x + "%");
      node.style.setProperty("--dff-node-y", y + "%");
      node.style.setProperty("--dff-node-delay", (i * 80 + index * 55) + "ms");
      node.style.setProperty("--dff-node-scale", String(0.72 + ((i + index) % 4) * 0.12));
      visual.appendChild(node);
    }

    card.appendChild(visual);
    card.style.setProperty("--dff-card-density", String(clamp(value / 20, 0.12, 0.44)));
  }

  document.querySelectorAll("[data-dff-metric-card]").forEach(addMetricVisual);

  function toast(message) {
    var region = document.querySelector("[data-dff-toast-region]");
    if (!region) {
      return;
    }
    var item = document.createElement("div");
    item.className = "dff-toast";
    item.textContent = message;
    region.appendChild(item);
    window.setTimeout(function () {
      item.classList.add("dff-toast-exit");
      window.setTimeout(function () {
        item.remove();
      }, prefersReducedMotion ? 0 : 180);
    }, 2200);
  }

  function copyText(text) {
    if (!text) {
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(
        function () {
          toast("Copied to clipboard");
        },
        function () {
          toast("Copy failed");
        }
      );
      return;
    }
    toast("Clipboard unavailable");
  }

  function setupCopyButtons() {
    document.addEventListener("click", function (event) {
      var directCopy = event.target.closest("[data-dff-copy]");
      if (directCopy) {
        copyText(directCopy.getAttribute("data-dff-copy"));
        return;
      }

      var targetCopy = event.target.closest("[data-dff-copy-target]");
      if (!targetCopy) {
        return;
      }
      var selector = targetCopy.getAttribute("data-dff-copy-target");
      var target = selector ? document.querySelector(selector) : null;
      copyText(target ? target.textContent : "");
    });
  }

  function setupThemeToggle() {
    var toggle = document.querySelector("[data-dff-theme-toggle]");
    var page = document.documentElement;
    if (!toggle || !page) {
      return;
    }

    function setTheme(theme) {
      page.setAttribute("data-dff-theme", theme);
      toggle.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      var next = page.getAttribute("data-dff-theme") === "dark" ? "light" : "dark";
      setTheme(next);
      toast(next === "dark" ? "Dark theme enabled" : "Light theme enabled");
    });

    setTheme(page.getAttribute("data-dff-theme") || "light");
  }

  function setupCommandSearch() {
    var search = document.querySelector("[data-dff-command-search]");
    if (!search) {
      return;
    }
    document.addEventListener("keydown", function (event) {
      var key = event.key ? event.key.toLowerCase() : "";
      if ((event.metaKey || event.ctrlKey) && key === "k") {
        event.preventDefault();
        search.focus();
        search.select();
        toast("Search focused");
      }
    });
  }

  function enhanceClickTargets() {
    var targets = document.querySelectorAll(
      "a, button, .dff-metric-card, .dff-board-stat, .dff-quick-actions a, .dff-review-list a, .dff-table-action"
    );
    targets.forEach(function (target) {
      target.classList.add("dff-interactive");
      target.addEventListener("pointerdown", function () {
        target.classList.add("dff-is-pressed");
      });
      target.addEventListener("pointerup", function () {
        target.classList.remove("dff-is-pressed");
      });
      target.addEventListener("pointerleave", function () {
        target.classList.remove("dff-is-pressed");
      });
    });
  }

  function firstControl(section) {
    return section ? section.querySelector("input:not([type=hidden]), select, textarea, button") : null;
  }

  function controlHasValue(control) {
    if (!control) {
      return false;
    }
    if (control.type === "checkbox" || control.type === "radio") {
      return control.checked;
    }
    return String(control.value || "").trim().length > 0;
  }

  function setupFlagForm() {
    var form = document.querySelector("[data-dff-flag-form]");
    if (!form) {
      return;
    }

    var steps = Array.prototype.slice.call(document.querySelectorAll("[data-dff-step-target]"));
    var sections = Array.prototype.slice.call(document.querySelectorAll("[data-dff-form-section]"));
    var fields = Array.prototype.slice.call(form.querySelectorAll("[data-dff-field]"));

    function activateStep(name) {
      steps.forEach(function (step) {
        var isActive = step.getAttribute("data-dff-step-target") === name;
        step.classList.toggle("dff-form-step-active", isActive);
        if (isActive) {
          step.setAttribute("aria-current", "step");
        } else {
          step.removeAttribute("aria-current");
        }
      });

      sections.forEach(function (section) {
        section.classList.toggle("dff-form-section-active", section.getAttribute("data-dff-form-section") === name);
      });
    }

    function updateField(field) {
      var control = firstControl(field);
      field.classList.toggle("dff-field-has-value", controlHasValue(control));
    }

    fields.forEach(function (field) {
      var control = firstControl(field);
      updateField(field);
      if (!control) {
        return;
      }
      control.addEventListener("focus", function () {
        field.classList.add("dff-field-active");
        var section = field.closest("[data-dff-form-section]");
        if (section) {
          activateStep(section.getAttribute("data-dff-form-section"));
        }
      });
      control.addEventListener("blur", function () {
        field.classList.remove("dff-field-active");
        updateField(field);
      });
      control.addEventListener("input", function () {
        updateField(field);
      });
      control.addEventListener("change", function () {
        updateField(field);
      });
    });

    steps.forEach(function (step) {
      step.addEventListener("click", function () {
        var targetName = step.getAttribute("data-dff-step-target");
        var target = document.querySelector('[data-dff-form-section="' + targetName + '"]');
        if (!target) {
          return;
        }
        activateStep(targetName);
        target.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "center" });
        var control = firstControl(target);
        if (control && !target.matches(".dff-side-panel")) {
          window.setTimeout(function () {
            control.focus({ preventScroll: true });
          }, prefersReducedMotion ? 0 : 260);
        }
      });
    });

    if ("IntersectionObserver" in window && sections.length) {
      var sectionObserver = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              activateStep(entry.target.getAttribute("data-dff-form-section"));
            }
          });
        },
        { threshold: 0.48 }
      );
      sections.forEach(function (section) {
        sectionObserver.observe(section);
      });
    }

    form.addEventListener("submit", function () {
      var submit = form.querySelector("[data-dff-launch-submit]");
      if (submit) {
        submit.classList.add("dff-launching");
      }
    });

    activateStep("identity");
  }

  enhanceClickTargets();
  setupCopyButtons();
  setupThemeToggle();
  setupCommandSearch();
  setupFlagForm();

  if (!prefersReducedMotion) {
    window.addEventListener(
      "pointermove",
      function (event) {
        var x = Math.round((event.clientX / Math.max(window.innerWidth, 1)) * 100);
        var y = Math.round((event.clientY / Math.max(window.innerHeight, 1)) * 100);
        root.style.setProperty("--dff-pointer-x", x);
        root.style.setProperty("--dff-pointer-y", y);
        root.style.setProperty("--dff-pointer-shift-x", (x - 50) + "px");
        root.style.setProperty("--dff-pointer-shift-y", (y - 50) + "px");
      },
      { passive: true }
    );
  }

  var rows = document.querySelectorAll(".dff-flag-board-row");
  if ("IntersectionObserver" in window && rows.length) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("dff-row-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.18 }
    );

    rows.forEach(function (row) {
      observer.observe(row);
    });
  } else {
    rows.forEach(function (row) {
      row.classList.add("dff-row-visible");
    });
  }
})();
