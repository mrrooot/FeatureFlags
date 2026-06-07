(function () {
  function listFor(button) {
    var type = button.getAttribute("data-add");
    var section = button.closest('[data-list="' + type + '"]');
    return section ? section.querySelector('[data-items="' + type + '"]') : null;
  }

  function nextIndex(container, type) {
    return container.querySelectorAll('[name="' + type + '_index"]').length;
  }

  function renderTemplate(type, index) {
    var template = document.querySelector('[data-template="' + type + '"]');
    if (!template) {
      return null;
    }
    var fragment = template.content.cloneNode(true);
    var wrapper = document.createElement("div");
    wrapper.appendChild(fragment);
    wrapper.innerHTML = wrapper.innerHTML.replace(/__index__/g, String(index));
    return wrapper.firstElementChild;
  }

  function clearEmptyState(container) {
    var empty = container.querySelector(".dff-empty-state");
    if (empty) {
      empty.remove();
    }
  }

  function markDirty(target) {
    var form = target.closest("[data-targeting-form]");
    if (!form) {
      return;
    }
    form.classList.add("dff-is-dirty");
    var section = target.closest(".dff-targeting-section");
    if (section) {
      section.classList.add("dff-section-dirty");
    }
    var countTarget = form.querySelector("[data-dirty-count]");
    if (countTarget) {
      countTarget.textContent = String(form.querySelectorAll(".dff-section-dirty").length);
    }
  }

  function addRow(button) {
    var type = button.getAttribute("data-add");
    var container = listFor(button);
    if (!container) {
      return;
    }
    var row = renderTemplate(type, nextIndex(container, type));
    if (!row) {
      return;
    }
    clearEmptyState(container);
    container.appendChild(row);
    markDirty(button);
    var firstControl = row.querySelector("input:not([type=hidden]), select, textarea");
    if (firstControl) {
      firstControl.focus();
    }
  }

  function removeRow(button) {
    var row = button.closest(".dff-builder-row, .dff-rule-block");
    if (row) {
      markDirty(button);
      row.remove();
    }
  }

  function switchEnvironment(select) {
    var value = select.value;
    if (value) {
      window.location = "?environment=" + encodeURIComponent(value);
    }
  }

  document.addEventListener("click", function (event) {
    var addButton = event.target.closest("[data-add]");
    if (addButton) {
      event.preventDefault();
      addRow(addButton);
      return;
    }

    var removeButton = event.target.closest("[data-remove]");
    if (removeButton) {
      event.preventDefault();
      removeRow(removeButton);
    }
  });

  document.addEventListener("change", function (event) {
    var switcher = event.target.closest("[data-environment-switch]");
    if (switcher) {
      switchEnvironment(switcher);
      return;
    }
    if (event.target.closest("[data-targeting-form]")) {
      markDirty(event.target);
    }
  });

  document.addEventListener("input", function (event) {
    if (event.target.closest("[data-targeting-form]")) {
      markDirty(event.target);
    }
  });
})();
