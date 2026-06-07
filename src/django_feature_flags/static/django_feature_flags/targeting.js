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
    var firstControl = row.querySelector("input:not([type=hidden]), select, textarea");
    if (firstControl) {
      firstControl.focus();
    }
  }

  function removeRow(button) {
    var row = button.closest(".dff-builder-row, .dff-rule-block");
    if (row) {
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
    }
  });
})();
