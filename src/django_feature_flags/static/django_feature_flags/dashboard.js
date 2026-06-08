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
