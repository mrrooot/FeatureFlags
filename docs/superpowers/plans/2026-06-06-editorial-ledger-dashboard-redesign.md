# Editorial Ledger Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Django Feature Flags dashboard overview, flags list, and create flag form into a polished Editorial Ledger Workspace without changing routes, models, or flag behavior.

**Architecture:** Keep the current Django dashboard app and template boundaries. Use template-visible contract tests for the new screen structure, then update `base.html`, the three dashboard templates, and `dashboard.css` as a cohesive CSS-only redesign. The redesign uses existing view data and the existing `FeatureFlagCreateForm`.

**Tech Stack:** Django templates, Django static CSS, pytest, Django test client, Django system checks.

---

## File Structure

- Modify `tests/test_dashboard.py`: add visible contract tests for the new overview, flag ledger, and create form copy.
- Modify `src/django_feature_flags/templates/django_feature_flags/base.html`: update the shared shell, sidebar, message layout, and main content wrapper.
- Modify `src/django_feature_flags/templates/django_feature_flags/dashboard.html`: build the command desk overview using existing `project_count`, `flag_count`, `recent_flags`, and `style_name`.
- Modify `src/django_feature_flags/templates/django_feature_flags/flag_list.html`: build the ledger table using existing `flag_rows`.
- Modify `src/django_feature_flags/templates/django_feature_flags/flag_form.html`: build the guided create form using existing `form`.
- Replace most of `src/django_feature_flags/static/django_feature_flags/dashboard.css`: define the Editorial Ledger visual system, shared controls, tables, forms, alerts, and responsive behavior.

No new runtime dependencies, static assets, JavaScript files, routes, migrations, or models are required.

---

### Task 1: Add Dashboard Redesign Contract Tests

**Files:**
- Modify: `tests/test_dashboard.py`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Add failing tests for the approved visible structure**

Append these tests to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_overview_uses_editorial_ledger_workspace(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=default)
    client.force_login(staff_user)

    response = client.get("/flags/")

    assert response.status_code == 200
    assert b"Editorial Ledger" in response.content
    assert b"Release posture" in response.content
    assert b"Latest flag ledger" in response.content
    assert b"new_checkout" in response.content


@pytest.mark.django_db
def test_flag_list_uses_ledger_language_and_status_stamps(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=staging, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"Flag ledger" in response.content
    assert b"Configured off" in response.content
    assert b"staging" in response.content
    assert b"Recommendations" in response.content


@pytest.mark.django_db
def test_create_flag_form_uses_guided_editorial_copy(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    Environment.objects.create(project=project, key="staging", name="Staging")
    client.force_login(staff_user)

    response = client.get("/flags/flags/new/")

    assert response.status_code == 200
    assert b"Setup ledger" in response.content
    assert b"Default variation" in response.content
    assert b"Safely off" in response.content
```

- [ ] **Step 2: Run dashboard tests and verify the new tests fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: the existing tests pass and the three new tests fail because the current templates do not contain `Editorial Ledger`, `Release posture`, `Latest flag ledger`, `Flag ledger`, `Setup ledger`, `Default variation`, or `Safely off`.

- [ ] **Step 3: Leave the failing tests uncommitted**

Do not commit after this task. The next tasks make these tests pass.

---

### Task 2: Build The Shared Editorial Ledger Shell

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/base.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Update the shared shell in `base.html`**

Replace the `<body>` content in `base.html` with this structure while keeping the same static stylesheet link:

```html
<body>
  <aside class="dff-sidebar" aria-label="Feature flags navigation">
    <div class="dff-brand">
      <span class="dff-brand-mark">FF</span>
      <span>
        <strong>FeatureFlow</strong>
        <small>Editorial Ledger</small>
      </span>
    </div>
    <nav>
      <a href="{% url 'django_feature_flags_dashboard:home' %}">Overview</a>
      <a href="{% url 'django_feature_flags_dashboard:flag_list' %}">Flags</a>
      <a href="#">Segments</a>
      <a href="#">Experiments</a>
      <a href="#">Metrics</a>
      <a href="#">Approvals</a>
      <a href="#">Audit</a>
    </nav>
  </aside>
  <main class="dff-main" id="main">
    {% if messages %}
    <div class="dff-messages" aria-live="polite">
      {% for message in messages %}
      <div class="dff-alert dff-alert-{{ message.tags }}">{{ message }}</div>
      {% endfor %}
    </div>
    {% endif %}
    {% block content %}{% endblock %}
  </main>
</body>
```

- [ ] **Step 2: Replace the stylesheet foundation**

Replace the top-level tokens and shared selectors in `dashboard.css` with an Editorial Ledger foundation. Keep every selector ASCII-only and keep panel radii at `8px` or below.

Use these token names and values:

```css
:root {
  color-scheme: light;
  --dff-bg: #f2f4f1;
  --dff-bg-warm: #fbfaf6;
  --dff-panel: #ffffff;
  --dff-panel-soft: #f7f6ef;
  --dff-text: #172033;
  --dff-heading: #111827;
  --dff-muted: #667085;
  --dff-line: #d7d1c4;
  --dff-line-strong: #a99f91;
  --dff-ink: #172033;
  --dff-copper: #a6532d;
  --dff-copper-dark: #7c3c22;
  --dff-copper-soft: #f3ded1;
  --dff-teal: #0f766e;
  --dff-teal-soft: #d9f3ee;
  --dff-warning: #b45309;
  --dff-warning-soft: #f9e7bd;
  --dff-danger: #b42318;
  --dff-danger-soft: #fde3df;
  --dff-shadow: 0 18px 38px rgba(23, 32, 51, 0.08);
  --dff-focus: 0 0 0 3px rgba(166, 83, 45, 0.22);
}
```

Define these shared groups in the same stylesheet:

```css
body { grid-template-columns: 256px minmax(0, 1fr); background: var(--dff-bg); }
body::before { content: ""; position: fixed; inset: 0; pointer-events: none; opacity: .45; }
.dff-sidebar { background: var(--dff-ink); color: #fff; }
.dff-brand { display: flex; align-items: center; gap: 12px; }
.dff-brand-mark { display: inline-grid; place-items: center; width: 42px; height: 42px; border-radius: 8px; background: var(--dff-copper); }
.dff-main { padding: 34px; max-width: 1320px; }
.dff-header { align-items: flex-start; border-bottom: 1px solid var(--dff-line); padding-bottom: 20px; }
.dff-kicker { color: var(--dff-copper); text-transform: uppercase; }
h1 { font-family: Georgia, "Times New Roman", serif; font-size: 36px; line-height: 1.05; }
.dff-button { min-height: 40px; border-radius: 7px; }
.dff-button-primary { background: var(--dff-copper); color: #fff; }
.dff-button-secondary { background: var(--dff-panel); color: var(--dff-text); border-color: var(--dff-line); }
.dff-panel { border: 1px solid var(--dff-line); border-radius: 8px; background: var(--dff-panel); box-shadow: var(--dff-shadow); }
.dff-alert-success { border-color: var(--dff-teal); background: var(--dff-teal-soft); color: var(--dff-teal); }
.dff-alert-error { border-color: var(--dff-danger); background: var(--dff-danger-soft); color: var(--dff-danger); }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible { outline: 0; box-shadow: var(--dff-focus); }
```

- [ ] **Step 3: Run the dashboard tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: the three new tests still fail because the individual screen content is not redesigned yet. No template syntax errors should appear.

---

### Task 3: Redesign The Overview Command Desk

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/dashboard.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py::test_overview_uses_editorial_ledger_workspace`

- [ ] **Step 1: Replace the overview template content**

In `dashboard.html`, keep `{% extends %}` and `{% block content %}`. Replace the block body with this structure:

```html
<header class="dff-header dff-command-header">
  <div>
    <p class="dff-kicker">{{ style_name }} / Editorial Ledger</p>
    <h1>Control Center</h1>
    <p class="dff-subtitle">A polished command desk for reviewing projects, flags, and release posture from your Django app.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_list' %}">View ledger</a>
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">New flag</a>
  </div>
</header>

<section class="dff-command-grid">
  <div class="dff-kpi-grid">
    <article class="dff-panel dff-kpi-card">
      <span class="dff-label">Projects</span>
      <strong>{{ project_count }}</strong>
      <p>Workspaces currently registered for flag control.</p>
    </article>
    <article class="dff-panel dff-kpi-card">
      <span class="dff-label">Flags</span>
      <strong>{{ flag_count }}</strong>
      <p>Feature decisions available to environments and SDKs.</p>
    </article>
    <article class="dff-panel dff-kpi-card dff-kpi-card-accent">
      <span class="dff-label">Experiment health</span>
      <strong>Ready</strong>
      <p>Evaluation, events, and audit foundations are installed.</p>
    </article>
  </div>

  <aside class="dff-panel dff-posture-panel">
    <p class="dff-kicker">Release posture</p>
    <h2>Controlled by default</h2>
    <p>New flags start with explicit variations and environment states so production changes can be reviewed before rollout.</p>
    <div class="dff-posture-list">
      <span>Audit trail ready</span>
      <span>Environment scoped</span>
      <span>SDK key protected</span>
    </div>
  </aside>
</section>

<section class="dff-section">
  <div class="dff-section-header">
    <div>
      <p class="dff-kicker">Recent activity</p>
      <h2>Latest flag ledger</h2>
    </div>
    <a class="dff-link" href="{% url 'django_feature_flags_dashboard:flag_list' %}">Open all flags</a>
  </div>
  <div class="dff-panel dff-panel-flush">
    {% if recent_flags %}
    <table class="dff-table">
      <thead>
        <tr>
          <th>Flag</th>
          <th>Project</th>
          <th>Type</th>
          <th>State</th>
        </tr>
      </thead>
      <tbody>
        {% for flag in recent_flags %}
        <tr>
          <td><strong>{{ flag.key }}</strong><span>{{ flag.name }}</span></td>
          <td>{{ flag.project.key }}</td>
          <td><span class="dff-badge">{{ flag.value_type }}</span></td>
          <td>
            {% if flag.archived %}
            <span class="dff-badge dff-badge-muted">Archived</span>
            {% else %}
            <span class="dff-badge dff-badge-success">Ready</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="dff-empty">
      <strong>No flags in the ledger</strong>
      <span>Create the first flag and attach it to staging, production, or any project environment.</span>
      <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">New flag</a>
    </div>
    {% endif %}
  </div>
</section>
```

- [ ] **Step 2: Add overview layout CSS**

Add these classes to `dashboard.css`:

```css
.dff-command-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: stretch; }
.dff-kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.dff-kpi-card { min-height: 160px; display: grid; align-content: space-between; }
.dff-kpi-card strong { font-family: Georgia, "Times New Roman", serif; font-size: 34px; line-height: 1; }
.dff-kpi-card p, .dff-posture-panel p { margin: 0; color: var(--dff-muted); }
.dff-kpi-card-accent { background: var(--dff-ink); color: #fff; border-color: var(--dff-ink); }
.dff-kpi-card-accent .dff-label, .dff-kpi-card-accent p { color: #d7dee8; }
.dff-posture-panel { display: grid; gap: 14px; background: linear-gradient(180deg, #fff, var(--dff-panel-soft)); }
.dff-posture-list { display: grid; gap: 8px; }
.dff-posture-list span { border-top: 1px solid var(--dff-line); padding-top: 9px; color: var(--dff-text); font-weight: 750; }
.dff-link { color: var(--dff-copper); font-weight: 800; text-decoration: none; }
.dff-link:hover { color: var(--dff-copper-dark); }
```

- [ ] **Step 3: Run the overview test and dashboard tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_overview_uses_editorial_ledger_workspace -q
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: the overview test passes. The flags-list and form redesign tests still fail until their tasks are complete.

---

### Task 4: Redesign The Flags Ledger

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py::test_flag_list_uses_ledger_language_and_status_stamps`

- [ ] **Step 1: Replace the flags list template block**

In `flag_list.html`, keep `{% extends %}` and `{% block content %}`. Replace the block body with this structure:

```html
<header class="dff-header">
  <div>
    <p class="dff-kicker">{{ style_name }} / Flag ledger</p>
    <h1>Flag ledger</h1>
    <p class="dff-subtitle">Scan rollout defaults, project ownership, and environment posture from one operational table.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">New flag</a>
  </div>
</header>

<section class="dff-panel dff-panel-flush">
  {% if flag_rows %}
  <table class="dff-table dff-ledger-table">
    <thead>
      <tr>
        <th>Flag</th>
        <th>Project</th>
        <th>Type</th>
        <th>Environments</th>
        <th>Status</th>
      </tr>
    </thead>
    <tbody>
      {% for row in flag_rows %}
      <tr>
        <td><strong>{{ row.flag.key }}</strong><span>{{ row.flag.name }}</span></td>
        <td><span class="dff-project-stamp">{{ row.flag.project.key }}</span></td>
        <td><span class="dff-badge">{{ row.flag.value_type }}</span></td>
        <td>
          <div class="dff-chip-row">
            {% for state in row.states %}
            <span class="dff-chip">{{ state.environment.key }}</span>
            {% empty %}
            <span class="dff-muted-text">No states</span>
            {% endfor %}
          </div>
        </td>
        <td>
          {% if row.flag.archived %}
          <span class="dff-badge dff-badge-muted">Archived</span>
          {% elif row.enabled_count %}
          <span class="dff-badge dff-badge-success">{{ row.enabled_count }} enabled</span>
          {% else %}
          <span class="dff-badge dff-badge-warning">Configured off</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="dff-empty">
    <strong>No flags in the ledger</strong>
    <span>Create a project flag, choose its environments, and the package will generate its default variation and states.</span>
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">New flag</a>
  </div>
  {% endif %}
</section>
```

- [ ] **Step 2: Add ledger table CSS**

Add or update these selectors in `dashboard.css`:

```css
.dff-table { width: 100%; border-collapse: collapse; background: var(--dff-panel); }
.dff-table th, .dff-table td { padding: 16px 14px; border-bottom: 1px solid var(--dff-line); text-align: left; vertical-align: middle; }
.dff-table th { color: var(--dff-muted); font-size: 11px; font-weight: 900; text-transform: uppercase; }
.dff-table td strong { display: block; color: var(--dff-heading); font-size: 14px; }
.dff-table td span { display: block; color: var(--dff-muted); font-size: 12px; margin-top: 4px; }
.dff-ledger-table tbody tr:hover { background: #fbfaf6; }
.dff-project-stamp { display: inline-flex; width: max-content; margin: 0; border-bottom: 2px solid var(--dff-copper-soft); color: var(--dff-text); font-weight: 800; }
.dff-badge, .dff-table td .dff-badge { display: inline-flex; width: max-content; align-items: center; min-height: 25px; border-radius: 999px; padding: 0 10px; margin: 0; background: #eee9df; color: var(--dff-text); font-size: 12px; font-weight: 850; }
.dff-badge-success { background: var(--dff-teal-soft); color: var(--dff-teal); }
.dff-badge-warning { background: var(--dff-warning-soft); color: var(--dff-warning); }
.dff-badge-muted { background: #e5e1d8; color: #625a50; }
.dff-chip-row { display: flex; flex-wrap: wrap; gap: 6px; }
.dff-chip, .dff-table td .dff-chip { display: inline-flex; align-items: center; min-height: 25px; border: 1px solid var(--dff-line); border-radius: 999px; padding: 0 9px; margin: 0; background: #fff; color: var(--dff-text); font-size: 12px; font-weight: 750; }
```

- [ ] **Step 3: Run the flags-list test and dashboard tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_flag_list_uses_ledger_language_and_status_stamps -q
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: the flags-list test passes. The form redesign test still fails until the create form task is complete.

---

### Task 5: Redesign The Create Flag Form

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_form.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py::test_create_flag_form_uses_guided_editorial_copy`

- [ ] **Step 1: Replace the create form template block**

In `flag_form.html`, keep `{% extends %}` and `{% block content %}`. Replace the block body with this structure:

```html
<header class="dff-header">
  <div>
    <p class="dff-kicker">{{ style_name }} / Setup ledger</p>
    <h1>Create flag</h1>
    <p class="dff-subtitle">Define the first default value and attach the flag to project environments with a safe initial posture.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_list' %}">Back to ledger</a>
  </div>
</header>

<section class="dff-form-layout">
  <form class="dff-panel dff-form" method="post">
    {% csrf_token %}

    {% if form.non_field_errors %}
    <div class="dff-alert dff-alert-error">{{ form.non_field_errors }}</div>
    {% endif %}

    <div class="dff-form-section">
      <p class="dff-kicker">Setup ledger</p>
      <h2>Flag identity</h2>
      <div class="dff-form-grid">
        <div class="dff-field">
          <label for="{{ form.project.id_for_label }}">Project</label>
          {{ form.project }}
          {{ form.project.errors }}
        </div>
        <div class="dff-field">
          <label for="{{ form.key.id_for_label }}">Flag key</label>
          {{ form.key }}
          {% if form.key.help_text %}<small>{{ form.key.help_text }}</small>{% endif %}
          {{ form.key.errors }}
        </div>
        <div class="dff-field">
          <label for="{{ form.name.id_for_label }}">Display name</label>
          {{ form.name }}
          {{ form.name.errors }}
        </div>
        <div class="dff-field">
          <label for="{{ form.value_type.id_for_label }}">Value type</label>
          {{ form.value_type }}
          {{ form.value_type.errors }}
        </div>
      </div>
    </div>

    <div class="dff-form-section">
      <h2>Default variation</h2>
      <div class="dff-form-grid">
        <div class="dff-field dff-field-full">
          <label for="{{ form.description.id_for_label }}">Description</label>
          {{ form.description }}
          {{ form.description.errors }}
        </div>
        <div class="dff-field dff-field-full">
          <label for="{{ form.default_value.id_for_label }}">Default value</label>
          {{ form.default_value }}
          {% if form.default_value.help_text %}<small>{{ form.default_value.help_text }}</small>{% endif %}
          {{ form.default_value.errors }}
        </div>
        <fieldset class="dff-field dff-field-full">
          <legend>Environments</legend>
          <div class="dff-checkbox-list">{{ form.environments }}</div>
          {{ form.environments.errors }}
        </fieldset>
      </div>
    </div>

    <div class="dff-form-actions">
      <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_list' %}">Cancel</a>
      <button class="dff-button dff-button-primary" type="submit">Create flag</button>
    </div>
  </form>

  <aside class="dff-panel dff-side-panel">
    <p class="dff-kicker">Safely off</p>
    <h2>Default variation</h2>
    <p>The package creates one default variation and disabled states for every selected environment.</p>
    <div class="dff-side-list">
      <span>Project scoped key</span>
      <span>Validation before save</span>
      <span>Disabled rollout states</span>
    </div>
  </aside>
</section>
```

- [ ] **Step 2: Add editorial form CSS**

Add or update these selectors in `dashboard.css`:

```css
.dff-form-layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
.dff-form { display: grid; gap: 22px; }
.dff-form-section { display: grid; gap: 14px; padding-bottom: 18px; border-bottom: 1px solid var(--dff-line); }
.dff-form-section:last-of-type { border-bottom: 0; padding-bottom: 0; }
.dff-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.dff-field { min-width: 0; display: grid; gap: 8px; border: 0; padding: 0; margin: 0; }
.dff-field-full { grid-column: 1 / -1; }
.dff-field label, .dff-field legend { color: var(--dff-text); font-size: 13px; font-weight: 850; }
.dff-field input, .dff-field select, .dff-field textarea { width: 100%; min-height: 43px; border: 1px solid var(--dff-line); border-radius: 7px; padding: 10px 12px; box-sizing: border-box; background: #fff; color: var(--dff-text); font: inherit; }
.dff-field textarea { resize: vertical; }
.dff-field small { color: var(--dff-muted); }
.dff-checkbox-list { border: 1px solid var(--dff-line); border-radius: 8px; padding: 8px; background: var(--dff-panel-soft); }
.dff-checkbox-list label { min-height: 36px; display: flex; align-items: center; gap: 9px; padding: 0 8px; border-radius: 7px; color: var(--dff-text); font-weight: 750; }
.dff-checkbox-list label:hover { background: #fff; }
.dff-checkbox-list input { width: 16px; min-height: 16px; }
.errorlist { list-style: none; margin: 0; padding: 0; color: var(--dff-danger); font-size: 13px; font-weight: 800; }
.dff-form-actions { justify-content: flex-end; border-top: 1px solid var(--dff-line); padding-top: 18px; }
.dff-side-panel { display: grid; gap: 13px; background: linear-gradient(180deg, #fff, var(--dff-panel-soft)); }
.dff-side-panel p { margin: 0; color: var(--dff-muted); }
.dff-side-list { display: grid; gap: 8px; }
.dff-side-list span { border: 1px solid var(--dff-line); border-radius: 7px; padding: 10px 11px; background: #fff; color: var(--dff-text); font-weight: 800; }
```

- [ ] **Step 3: Run the create-form test and dashboard tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_create_flag_form_uses_guided_editorial_copy -q
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: all dashboard tests pass.

---

### Task 6: Responsive And Accessibility Polish

**Files:**
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Add responsive rules**

Add these media rules at the bottom of `dashboard.css`:

```css
@media (max-width: 1040px) {
  .dff-command-grid,
  .dff-form-layout {
    grid-template-columns: 1fr;
  }

  .dff-kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  body {
    grid-template-columns: 1fr;
  }

  .dff-sidebar {
    position: static;
  }

  .dff-sidebar nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dff-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .dff-form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 620px) {
  .dff-main {
    padding: 20px;
  }

  .dff-sidebar {
    padding: 18px;
  }

  .dff-sidebar nav {
    grid-template-columns: 1fr 1fr;
  }

  .dff-kpi-grid {
    grid-template-columns: 1fr;
  }

  .dff-panel-flush {
    overflow-x: auto;
  }

  .dff-table {
    min-width: 720px;
  }

  .dff-actions,
  .dff-form-actions {
    width: 100%;
  }

  .dff-button {
    flex: 1 1 auto;
  }
}
```

- [ ] **Step 2: Run dashboard tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py -q
```

Expected: all dashboard tests pass.

---

### Task 7: Full Verification And Commit

**Files:**
- Verify: all modified files

- [ ] **Step 1: Run whitespace check**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors. Windows line-ending notices are acceptable.

- [ ] **Step 2: Run full tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: all tests pass, including the dashboard tests.

- [ ] **Step 3: Run Django system check**

Run:

```powershell
$env:PYTHONPATH='src;.'; .venv\Scripts\python.exe -m django check --settings=tests.settings
```

Expected: `System check identified no issues (0 silenced).`

- [ ] **Step 4: Attempt browser visual pass**

Use the current local browser or a reachable local preview. Verify:

- Overview shows `Editorial Ledger`, KPI ledger cards, `Release posture`, and `Latest flag ledger`.
- Flags list shows `Flag ledger`, environment chips, and status stamps.
- Create form shows `Setup ledger`, `Default variation`, and `Safely off`.
- No visible text overlaps at desktop width.

If a local preview cannot be reached cleanly, record the exact preview failure in the implementation summary and continue only if tests and Django checks pass.

- [ ] **Step 5: Inspect final diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected: only dashboard templates, CSS, and `tests/test_dashboard.py` changed.

- [ ] **Step 6: Commit the redesign**

Run:

```powershell
git add tests/test_dashboard.py src/django_feature_flags/templates/django_feature_flags/base.html src/django_feature_flags/templates/django_feature_flags/dashboard.html src/django_feature_flags/templates/django_feature_flags/flag_list.html src/django_feature_flags/templates/django_feature_flags/flag_form.html src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat: redesign dashboard as editorial ledger"
```

Expected: commit succeeds.

- [ ] **Step 7: Push if requested by the user**

Run only when the user wants the package updated on GitHub:

```powershell
git push origin master
```

Expected: `master -> master`.

---

## Self-Review

- Spec coverage: overview, flags list, create form, visual system, responsive states, accessibility, and verification all map to tasks above.
- Scope check: plan does not introduce models, routes, migrations, JavaScript, or frontend dependencies.
- Deferred-work scan: no deferred implementation notes or unresolved decisions remain.
- Type consistency: the tests use existing model names and view data (`Project`, `Environment`, `FeatureFlag`, `Variation`, `FlagState`, `recent_flags`, `flag_rows`, `form`).
