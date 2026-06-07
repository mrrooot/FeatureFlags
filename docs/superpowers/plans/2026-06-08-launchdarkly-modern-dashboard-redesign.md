# LaunchDarkly-Style Modern Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current dark Release Observatory dashboard with a modern LaunchDarkly-style feature flag console while preserving the existing server-rendered targeting workflow.

**Architecture:** Keep the Django dashboard as templates plus static CSS and lightweight JavaScript. Update tests to lock the new information architecture, then replace the app shell, overview, flag list, Targeting tab, and changed-state save interactions without touching targeting persistence or evaluator semantics.

**Tech Stack:** Django templates/views, plain CSS, plain JavaScript, pytest, pytest-django, Django system checks.

---

## Scope Check

The approved spec is one subsystem: the staff dashboard UI. It does not require a backend API clone, evaluator changes, model changes, or a frontend framework. The implementation should be completed as a single plan with small commits.

---

## Runtime Note

Use the commands that have already passed in this workspace:

```bash
python3.10 -m pytest -q
PYTHONPATH=src python3.10 -m django check --settings tests.settings
```

For focused dashboard checks, use:

```bash
python3.10 -m pytest tests/test_dashboard.py tests/test_dashboard_workflows.py -q
```

---

## File Structure

- Modify `tests/test_dashboard.py`: replace old observatory copy assertions with LaunchDarkly-style console assertions and add structure checks for the Targeting workspace and sticky save bar.
- Modify `src/django_feature_flags/templates/django_feature_flags/base.html`: replace the dark observatory shell with a light app shell, left navigation, and top context bar.
- Modify `src/django_feature_flags/templates/django_feature_flags/dashboard.html`: replace radar/timeline/dashboard metaphor sections with compact overview metrics, recent flags, review queue, and quick actions.
- Modify `src/django_feature_flags/templates/django_feature_flags/flag_list.html`: replace ledger metaphor copy with table-first feature flag list copy and status language.
- Modify `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`: restructure Targeting into LaunchDarkly-style ordered sections and add a sticky save/review bar.
- Modify `src/django_feature_flags/static/django_feature_flags/dashboard.css`: replace the dark neon visual system with a light enterprise UI system, responsive tables, rule cards, tabs, preview panel, and save bar styles.
- Modify `src/django_feature_flags/static/django_feature_flags/targeting.js`: keep add/remove behavior and add changed-state tracking for the sticky save bar.

No new models, migrations, evaluator changes, or package dependencies are part of this plan.

---

### Task 1: Update Dashboard Tests For The New Product Direction

**Files:**
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Replace old observatory assertions with LaunchDarkly-style dashboard assertions**

In `tests/test_dashboard.py`, replace `test_overview_uses_release_observatory_workspace` with:

```python
@pytest.mark.django_db
def test_overview_uses_launchdarkly_style_console(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Feature flag console" in content
    assert "Recently updated flags" in content
    assert "Needs review" in content
    assert "Quick actions" in content
    assert "new_checkout" in content
    assert "Release Observatory" not in content
    assert "dff-radar" not in content
    assert "Release timeline" not in content
```

- [ ] **Step 2: Replace clickable dashboard surface assertions**

In `tests/test_dashboard.py`, replace `test_overview_surfaces_are_clickable_controls` with:

```python
@pytest.mark.django_db
def test_overview_console_links_to_workflows(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'href="#"' not in content
    assert "dff-quick-actions" in content
    assert "dff-review-list" in content
    assert reverse("django_feature_flags_dashboard:segment_list") in content
    assert reverse("django_feature_flags_dashboard:experiment_list") in content
    assert reverse("django_feature_flags_dashboard:audit_list") in content
    assert reverse("django_feature_flags_dashboard:approval_list") in content
    assert reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}) in content
```

- [ ] **Step 3: Replace old flag list language assertions**

In `tests/test_dashboard.py`, replace `test_flag_list_uses_ledger_language_and_status_stamps` with:

```python
@pytest.mark.django_db
def test_flag_list_uses_feature_flag_console_table(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=staging, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Feature flags" in content
    assert "Create flag" in content
    assert "Targeting" in content
    assert "Configured off" in content
    assert "staging" in content
    assert "Recommendations" in content
    assert "Flag ledger" not in content
    assert "Scan mode" not in content
```

- [ ] **Step 4: Add a shell structure test**

Append this test to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_dashboard_shell_uses_light_console_structure(client, staff_user):
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'class="dff-app-shell"' in content
    assert 'class="dff-sidebar"' in content
    assert 'class="dff-topbar"' in content
    assert "Feature flags" in content
    assert "Segments" in content
    assert "Audit log" in content
    assert "Project" in content
    assert "Environment" in content
    assert "Release Observatory" not in content
```

- [ ] **Step 5: Add Targeting workspace structure assertions**

Replace `test_flag_detail_renders_launchdarkly_style_targeting_sections` with:

```python
@pytest.mark.django_db
def test_flag_detail_renders_modern_targeting_workspace(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Targeting" in content
    assert "If all prerequisites pass" in content
    assert "Individual targets" in content
    assert "Segment rules" in content
    assert "Custom rules" in content
    assert "Default rule" in content
    assert "When targeting is off" in content
    assert "Preview evaluation" in content
    assert "Unsaved changes" in content
    assert 'data-save-bar' in content
    assert "targeting.js" in content
```

- [ ] **Step 6: Run the focused tests and verify they fail**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py -q
```

Expected: FAIL because the current templates still render the observatory dashboard, ledger language, old shell, and no sticky save bar.

- [ ] **Step 7: Commit the failing tests**

```bash
git add tests/test_dashboard.py
git commit -m "test(dashboard): expect launchdarkly style console"
```

---

### Task 2: Replace The App Shell With A Light Console Foundation

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/base.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Replace the shell markup**

In `src/django_feature_flags/templates/django_feature_flags/base.html`, replace the `<body>` contents with:

```html
<body>
  <div class="dff-app-shell">
    <aside class="dff-sidebar" aria-label="Feature flags navigation">
      <a class="dff-brand" href="{% url 'django_feature_flags_dashboard:home' %}">
        <span class="dff-brand-mark">FF</span>
        <span>
          <strong>FeatureFlow</strong>
          <small>Feature flag console</small>
        </span>
      </a>
      <nav class="dff-sidebar-nav">
        <a href="{% url 'django_feature_flags_dashboard:flag_list' %}">Feature flags <span>Flags</span></a>
        <a href="{% url 'django_feature_flags_dashboard:segment_list' %}">Segments <span>Audiences</span></a>
        <a href="{% url 'django_feature_flags_dashboard:experiment_list' %}">Experiments <span>Tests</span></a>
        <a href="{% url 'django_feature_flags_dashboard:approval_list' %}">Approvals <span>Review</span></a>
        <a href="{% url 'django_feature_flags_dashboard:audit_list' %}">Audit log <span>Events</span></a>
      </nav>
    </aside>
    <div class="dff-workspace">
      <header class="dff-topbar" aria-label="Dashboard context">
        <div class="dff-context-control">
          <span>Project</span>
          <strong>All projects</strong>
        </div>
        <div class="dff-context-control">
          <span>Environment</span>
          <strong>All environments</strong>
        </div>
        <form class="dff-search" role="search">
          <label for="dff-global-search">Search</label>
          <input id="dff-global-search" type="search" name="q" aria-label="Search flags, segments, or keys">
        </form>
      </header>
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
    </div>
  </div>
</body>
```

- [ ] **Step 2: Replace the global CSS foundation**

In `src/django_feature_flags/static/django_feature_flags/dashboard.css`, replace the current dark root/body/sidebar/top-level styles with this foundation before component-specific styles are rebuilt in later tasks:

```css
:root {
  color-scheme: light;
  --dff-font-ui: Aptos, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  --dff-font-code: "Cascadia Code", "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  --dff-bg: #f6f8fb;
  --dff-surface: #ffffff;
  --dff-surface-muted: #f1f5f9;
  --dff-text: #111827;
  --dff-heading: #0f172a;
  --dff-muted: #64748b;
  --dff-line: #dbe3ef;
  --dff-line-strong: #bfccd9;
  --dff-accent: #315cf6;
  --dff-accent-dark: #243fbd;
  --dff-success: #12805c;
  --dff-warning: #a16207;
  --dff-danger: #b42318;
  --dff-radius: 8px;
  --dff-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  --dff-focus: 0 0 0 3px rgba(49, 92, 246, 0.2);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--dff-bg);
  color: var(--dff-text);
  font-family: var(--dff-font-ui);
  font-size: 14px;
}

a {
  color: inherit;
}

.dff-app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
}

.dff-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 20px 16px;
  border-right: 1px solid var(--dff-line);
  background: #fbfdff;
}

.dff-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  margin-bottom: 24px;
  color: var(--dff-heading);
  text-decoration: none;
}

.dff-brand-mark {
  display: inline-grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: var(--dff-heading);
  color: #ffffff;
  font-family: var(--dff-font-code);
  font-size: 12px;
  font-weight: 800;
}

.dff-brand strong,
.dff-brand small {
  display: block;
}

.dff-brand strong {
  font-size: 15px;
  line-height: 1.15;
}

.dff-brand small {
  margin-top: 2px;
  color: var(--dff-muted);
  font-size: 11px;
  font-weight: 700;
}

.dff-sidebar-nav {
  display: grid;
  gap: 4px;
}

.dff-sidebar-nav a {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 38px;
  padding: 0 10px;
  border-radius: var(--dff-radius);
  color: #334155;
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
}

.dff-sidebar-nav a:hover {
  background: #eef4ff;
  color: var(--dff-accent-dark);
}

.dff-sidebar-nav span {
  color: var(--dff-muted);
  font-size: 11px;
  font-weight: 600;
}

.dff-workspace {
  min-width: 0;
}

.dff-topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  min-height: 64px;
  display: grid;
  grid-template-columns: max-content max-content minmax(240px, 420px);
  align-items: center;
  gap: 12px;
  padding: 12px 28px;
  border-bottom: 1px solid var(--dff-line);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(12px);
}

.dff-context-control {
  min-height: 40px;
  min-width: 148px;
  display: grid;
  gap: 2px;
  padding: 7px 10px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  background: var(--dff-surface);
}

.dff-context-control span,
.dff-search label {
  color: var(--dff-muted);
  font-size: 11px;
  font-weight: 700;
}

.dff-context-control strong {
  color: var(--dff-heading);
  font-size: 13px;
}

.dff-search {
  display: grid;
  gap: 4px;
}

.dff-search input {
  width: 100%;
  height: 38px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 0 12px;
  background: var(--dff-surface);
  color: var(--dff-text);
  font: inherit;
}

.dff-search input:focus,
input:focus,
select:focus,
textarea:focus,
button:focus-visible,
a:focus-visible {
  outline: none;
  box-shadow: var(--dff-focus);
}

.dff-main {
  width: 100%;
  max-width: 1320px;
  padding: 28px;
}
```

- [ ] **Step 3: Remove old observatory-only selectors**

Delete CSS blocks whose selectors start with these prefixes because the new templates will not use them:

```text
.dff-sidebar-note
.dff-observatory-grid
.dff-radar-
.dff-command-map
.dff-command-card
.dff-timeline-
```

- [ ] **Step 4: Run the shell structure test**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py::test_dashboard_shell_uses_light_console_structure -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/django_feature_flags/templates/django_feature_flags/base.html src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat(dashboard): add light console shell"
```

---

### Task 3: Redesign Overview And Flag List As Product Console Pages

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/dashboard.html`
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Replace the dashboard overview template**

Replace `src/django_feature_flags/templates/django_feature_flags/dashboard.html` with:

```html
{% extends "django_feature_flags/base.html" %}

{% block content %}
<header class="dff-page-header">
  <div>
    <p class="dff-kicker">Overview</p>
    <h1>Feature flag console</h1>
    <p class="dff-subtitle">Monitor flags, audiences, approvals, and recent targeting changes from one workspace.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:segment_list' %}">Create segment</a>
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">Create flag</a>
  </div>
</header>

<section class="dff-metric-grid" aria-label="Workspace summary">
  <a class="dff-metric-card" href="{% url 'django_feature_flags_dashboard:flag_list' %}">
    <span>Flags</span>
    <strong>{{ flag_count }}</strong>
    <small>Feature decisions</small>
  </a>
  <a class="dff-metric-card" href="{% url 'django_feature_flags_dashboard:segment_list' %}">
    <span>Segments</span>
    <strong>{{ segment_count }}</strong>
    <small>Reusable audiences</small>
  </a>
  <a class="dff-metric-card" href="{% url 'django_feature_flags_dashboard:experiment_list' %}">
    <span>Experiments</span>
    <strong>{{ experiment_count }}</strong>
    <small>Running allocations</small>
  </a>
  <a class="dff-metric-card" href="{% url 'django_feature_flags_dashboard:approval_list' %}">
    <span>Needs review</span>
    <strong>{{ approval_count }}</strong>
    <small>Pending approvals</small>
  </a>
</section>

<section class="dff-dashboard-grid">
  <article class="dff-panel dff-panel-flush">
    <div class="dff-section-header">
      <div>
        <p class="dff-kicker">Flags</p>
        <h2>Recently updated flags</h2>
      </div>
      <a class="dff-link" href="{% url 'django_feature_flags_dashboard:flag_list' %}">View all</a>
    </div>
    {% if recent_flags %}
    <table class="dff-table">
      <thead>
        <tr>
          <th>Flag</th>
          <th>Project</th>
          <th>Type</th>
          <th>Environments</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {% for flag in recent_flags %}
        <tr>
          <td><strong class="dff-code">{{ flag.key }}</strong><span>{{ flag.name }}</span></td>
          <td>{{ flag.project.key }}</td>
          <td><span class="dff-status dff-status-neutral">{{ flag.value_type }}</span></td>
          <td>
            <div class="dff-chip-row">
              {% for state in flag.states.all %}
              <span class="dff-chip">{{ state.environment.key }}</span>
              {% empty %}
              <span class="dff-muted-text">No states</span>
              {% endfor %}
            </div>
          </td>
          <td>
            {% if flag.archived %}
            <span class="dff-status dff-status-archived">Archived</span>
            {% else %}
            <span class="dff-status dff-status-live">Ready</span>
            {% endif %}
          </td>
          <td><a class="dff-table-action" href="{% url 'django_feature_flags_dashboard:flag_detail' flag.pk %}">Open</a></td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% else %}
    <div class="dff-empty">
      <strong>No flags yet</strong>
      <span>Create a flag to start controlling rollout behavior by environment.</span>
      <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">Create flag</a>
    </div>
    {% endif %}
  </article>

  <aside class="dff-side-stack">
    <section class="dff-panel">
      <div class="dff-section-header">
        <div>
          <p class="dff-kicker">Review</p>
          <h2>Needs review</h2>
        </div>
        <a class="dff-link" href="{% url 'django_feature_flags_dashboard:approval_list' %}">Approvals</a>
      </div>
      <div class="dff-review-list">
        <a href="{% url 'django_feature_flags_dashboard:approval_list' %}">
          <strong>{{ approval_count }} pending</strong>
          <span>Review protected-environment changes before release.</span>
        </a>
        <a href="{% url 'django_feature_flags_dashboard:audit_list' %}">
          <strong>{{ audit_count }} audit events</strong>
          <span>Inspect the latest dashboard and approval activity.</span>
        </a>
      </div>
    </section>

    <section class="dff-panel">
      <div class="dff-section-header">
        <div>
          <p class="dff-kicker">Shortcuts</p>
          <h2>Quick actions</h2>
        </div>
      </div>
      <div class="dff-quick-actions">
        <a href="{% url 'django_feature_flags_dashboard:flag_create' %}">Create flag</a>
        <a href="{% url 'django_feature_flags_dashboard:segment_create' %}">Create segment</a>
        <a href="{% url 'django_feature_flags_dashboard:experiment_list' %}">Open experiments</a>
        <a href="{% url 'django_feature_flags_dashboard:audit_list' %}">Open audit log</a>
      </div>
    </section>
  </aside>
</section>
{% endblock %}
```

- [ ] **Step 2: Replace the flag list template**

Replace `src/django_feature_flags/templates/django_feature_flags/flag_list.html` with:

```html
{% extends "django_feature_flags/base.html" %}

{% block content %}
<header class="dff-page-header">
  <div>
    <p class="dff-kicker">Flags</p>
    <h1>Feature flags</h1>
    <p class="dff-subtitle">Open a flag to edit Targeting, Variations, Settings, and History.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">Create flag</a>
  </div>
</header>

<section class="dff-panel dff-panel-flush">
  {% if flag_rows %}
  <table class="dff-table dff-flag-table">
    <thead>
      <tr>
        <th>Flag</th>
        <th>Project</th>
        <th>Type</th>
        <th>Environments</th>
        <th>Targeting</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for row in flag_rows %}
      <tr>
        <td><strong class="dff-code">{{ row.flag.key }}</strong><span>{{ row.flag.name }}</span></td>
        <td>{{ row.flag.project.key }}</td>
        <td><span class="dff-status dff-status-neutral">{{ row.flag.value_type }}</span></td>
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
          <span class="dff-status dff-status-archived">Archived</span>
          {% elif row.enabled_count %}
          <span class="dff-status dff-status-live">{{ row.enabled_count }} on</span>
          {% else %}
          <span class="dff-status dff-status-off">Configured off</span>
          {% endif %}
        </td>
        <td><a class="dff-table-action" href="{% url 'django_feature_flags_dashboard:flag_detail' row.flag.pk %}">Open</a></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="dff-empty">
    <strong>No feature flags yet</strong>
    <span>Create a flag and each configured environment will start safely off.</span>
    <a class="dff-button dff-button-primary" href="{% url 'django_feature_flags_dashboard:flag_create' %}">Create flag</a>
  </div>
  {% endif %}
</section>
{% endblock %}
```

- [ ] **Step 3: Add overview and table CSS**

Append these component styles to `dashboard.css`:

```css
.dff-page-header,
.dff-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.dff-page-header {
  margin-bottom: 22px;
}

.dff-kicker {
  margin: 0 0 6px;
  color: var(--dff-accent-dark);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.dff-page-header h1,
.dff-section-header h2 {
  margin: 0;
  color: var(--dff-heading);
}

.dff-page-header h1 {
  font-size: 28px;
  line-height: 1.15;
}

.dff-section-header h2 {
  font-size: 16px;
}

.dff-subtitle {
  max-width: 720px;
  margin: 8px 0 0;
  color: var(--dff-muted);
  line-height: 1.5;
}

.dff-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dff-button,
.dff-table-action,
.dff-link {
  font-weight: 800;
  text-decoration: none;
}

.dff-button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--dff-radius);
  padding: 0 14px;
  font: inherit;
  cursor: pointer;
}

.dff-button-primary {
  background: var(--dff-accent);
  color: #ffffff;
}

.dff-button-primary:hover {
  background: var(--dff-accent-dark);
}

.dff-button-secondary {
  border-color: var(--dff-line);
  background: var(--dff-surface);
  color: var(--dff-heading);
}

.dff-panel {
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  background: var(--dff-surface);
  box-shadow: var(--dff-shadow);
}

.dff-panel-flush {
  overflow: hidden;
}

.dff-metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 22px;
}

.dff-metric-card {
  display: grid;
  gap: 6px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 16px;
  background: var(--dff-surface);
  color: inherit;
  text-decoration: none;
}

.dff-metric-card span,
.dff-metric-card small {
  color: var(--dff-muted);
}

.dff-metric-card strong {
  color: var(--dff-heading);
  font-size: 28px;
}

.dff-dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
}

.dff-side-stack {
  display: grid;
  gap: 18px;
}

.dff-panel > .dff-section-header,
.dff-panel .dff-empty {
  padding: 18px;
}

.dff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.dff-table th,
.dff-table td {
  border-top: 1px solid var(--dff-line);
  padding: 13px 16px;
  text-align: left;
  vertical-align: middle;
}

.dff-table thead th {
  border-top: 0;
  color: var(--dff-muted);
  background: var(--dff-surface-muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.dff-table td strong,
.dff-table td span {
  display: block;
}

.dff-code {
  font-family: var(--dff-font-code);
  font-size: 12px;
}

.dff-status,
.dff-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 0 9px;
  font-size: 11px;
  font-weight: 800;
}

.dff-status-neutral,
.dff-chip {
  background: #eef2f7;
  color: #334155;
}

.dff-status-live {
  background: #dcfce7;
  color: var(--dff-success);
}

.dff-status-off {
  background: #fff7ed;
  color: var(--dff-warning);
}

.dff-status-archived {
  background: #f3f4f6;
  color: #4b5563;
}

.dff-chip-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.dff-muted-text {
  color: var(--dff-muted);
}

.dff-table-action,
.dff-link {
  color: var(--dff-accent-dark);
}

.dff-empty {
  display: grid;
  gap: 8px;
  color: var(--dff-muted);
}

.dff-empty strong {
  color: var(--dff-heading);
  font-size: 16px;
}

.dff-review-list,
.dff-quick-actions {
  display: grid;
  gap: 8px;
  padding: 0 18px 18px;
}

.dff-review-list a,
.dff-quick-actions a {
  display: grid;
  gap: 4px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 12px;
  color: inherit;
  text-decoration: none;
}

.dff-review-list span {
  color: var(--dff-muted);
}
```

- [ ] **Step 4: Run overview and flag list tests**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py::test_overview_uses_launchdarkly_style_console tests/test_dashboard.py::test_overview_console_links_to_workflows tests/test_dashboard.py::test_flag_list_uses_feature_flag_console_table -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/django_feature_flags/templates/django_feature_flags/dashboard.html src/django_feature_flags/templates/django_feature_flags/flag_list.html src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat(dashboard): modernize overview and flag list"
```

---

### Task 4: Redesign The Targeting Tab As A LaunchDarkly-Style Workspace

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`
- Test: `tests/test_dashboard_workflows.py`

- [ ] **Step 1: Replace the flag detail header and tabs**

In `flag_detail.html`, replace the opening header and tabbar with:

```html
<header class="dff-page-header dff-flag-header">
  <div>
    <p class="dff-kicker">{{ flag.project.key }} / {{ state.environment.key }}</p>
    <h1>{{ flag.name }}</h1>
    <p class="dff-subtitle">
      <strong class="dff-code">{{ flag.key }}</strong>
      controls variation delivery for selected contexts in this environment.
    </p>
  </div>
  <div class="dff-actions">
    {% if state.enabled %}
    <span class="dff-status dff-status-live">Targeting on</span>
    {% else %}
    <span class="dff-status dff-status-off">Targeting off</span>
    {% endif %}
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_update' flag.pk %}">Settings</a>
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_list' %}">Back to flags</a>
  </div>
</header>

<nav class="dff-tabbar" aria-label="Flag sections">
  <span class="dff-tab dff-tab-active" aria-current="page">Targeting</span>
  <span class="dff-tab dff-tab-disabled">Variations</span>
  <a class="dff-tab" href="{% url 'django_feature_flags_dashboard:flag_update' flag.pk %}">Settings</a>
  <span class="dff-tab dff-tab-disabled">History</span>
</nav>
```

- [ ] **Step 2: Restructure the top Targeting controls**

Inside the existing form element with `class="dff-targeting-layout"` and `data-targeting-form`, replace the first environment/toggle/off variation blocks with this single top section:

```html
<section class="dff-panel dff-targeting-panel" aria-labelledby="targeting-form-heading">
  <div class="dff-targeting-section dff-targeting-state">
    <div>
      <span class="dff-label">Targeting</span>
      <h2 id="targeting-form-heading">Targeting rules for {{ state.environment.name|default:state.environment.key }}</h2>
      <p>If targeting is off, users receive the off variation and rules remain editable for later release.</p>
    </div>
    <label class="dff-field dff-field-compact" for="targeting-environment">
      <span>Environment</span>
      <select id="targeting-environment" name="targeting_environment_selector" data-environment-switch>
        {% for item in states %}
        <option value="{{ item.environment.key }}"{% if item.pk == state.pk %} selected{% endif %}>{{ item.environment.key }}</option>
        {% endfor %}
      </select>
    </label>
    <label class="dff-toggle" for="targeting-enabled">
      <input id="targeting-enabled" type="checkbox" name="enabled"{% if state.enabled %} checked{% endif %}>
      <span>Targeting on</span>
    </label>
    <label class="dff-field dff-field-compact" for="off-variation">
      <span>When targeting is off</span>
      <select id="off-variation" name="off_variation">
        {% for variation in variations %}
        <option value="{{ variation.key }}"{% if targeting.off_variation == variation.key %} selected{% endif %}>{{ variation.key }}</option>
        {% endfor %}
      </select>
    </label>
  </div>
```

- [ ] **Step 3: Rename and order Targeting sections**

In `flag_detail.html`, update the existing section headings to these exact labels:

```html
<span class="dff-label">Prerequisites</span>
<h2>If all prerequisites pass</h2>

<span class="dff-label">Direct matches</span>
<h2>Individual targets</h2>

<span class="dff-label">Reusable audiences</span>
<h2>Segment rules</h2>

<span class="dff-label">Rules</span>
<h2>Custom rules</h2>

<span class="dff-label">Fallback</span>
<h2>Default rule</h2>
```

Keep the existing input names unchanged so `TargetingDocumentForm` continues to parse the submitted form.

- [ ] **Step 4: Add IF/THEN wording to rule cards**

In each `.dff-rule-block`, add a numeric badge and labels:

```html
<div class="dff-rule-badge">Rule {{ forloop.counter }}</div>
```

Before the clause rows, add:

```html
<div class="dff-rule-language">IF all clauses match</div>
```

Before the serve selector, update the label text from `Serve` to:

```html
<span>THEN serve</span>
```

- [ ] **Step 5: Replace the preview panel heading**

In the preview aside, change:

```html
<h2 id="targeting-preview-heading">Preview</h2>
```

to:

```html
<h2 id="targeting-preview-heading">Preview evaluation</h2>
```

- [ ] **Step 6: Add Targeting workspace CSS**

Append these styles to `dashboard.css`:

```css
.dff-tabbar {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--dff-line);
}

.dff-tab {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 2px solid transparent;
  color: var(--dff-muted);
  text-decoration: none;
  font-weight: 800;
}

.dff-tab-active {
  border-bottom-color: var(--dff-accent);
  color: var(--dff-heading);
}

.dff-tab-disabled {
  color: #94a3b8;
}

.dff-targeting-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
}

.dff-targeting-panel {
  overflow: hidden;
}

.dff-targeting-section {
  display: grid;
  gap: 14px;
  padding: 18px;
  border-top: 1px solid var(--dff-line);
}

.dff-targeting-section:first-child {
  border-top: 0;
}

.dff-targeting-state {
  grid-template-columns: minmax(0, 1fr) 180px 160px 190px;
  align-items: end;
  background: #fbfdff;
}

.dff-targeting-state p {
  margin: 6px 0 0;
  color: var(--dff-muted);
}

.dff-label,
label span {
  color: var(--dff-muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.dff-field,
.dff-builder-row label,
.dff-rule-topline label,
.dff-clause-row label {
  display: grid;
  gap: 6px;
}

input,
select,
textarea {
  width: 100%;
  min-height: 38px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 8px 10px;
  background: var(--dff-surface);
  color: var(--dff-text);
  font: inherit;
}

textarea {
  resize: vertical;
}

.dff-toggle {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 0 10px;
  background: var(--dff-surface);
  font-weight: 800;
}

.dff-toggle input {
  width: auto;
  min-height: auto;
}

.dff-section-heading-row,
.dff-rule-topline,
.dff-builder-row,
.dff-clause-row {
  display: grid;
  gap: 12px;
  align-items: end;
}

.dff-section-heading-row {
  grid-template-columns: minmax(0, 1fr) max-content;
}

.dff-builder-row {
  grid-template-columns: minmax(160px, 1fr) minmax(140px, 180px) max-content;
}

.dff-builder-row-wide {
  grid-template-columns: 150px 170px minmax(220px, 1fr) max-content;
}

.dff-builder-grow {
  min-width: 0;
}

.dff-builder-list {
  display: grid;
  gap: 10px;
}

.dff-rule-block {
  position: relative;
  display: grid;
  gap: 12px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 14px;
  background: #fbfdff;
}

.dff-rule-badge,
.dff-rule-language {
  color: var(--dff-muted);
  font-size: 11px;
  font-weight: 900;
  text-transform: uppercase;
}

.dff-rule-topline {
  grid-template-columns: minmax(220px, 1fr) 180px max-content;
}

.dff-clause-row {
  grid-template-columns: 130px minmax(140px, 1fr) 150px minmax(160px, 1fr) 92px;
  border-top: 1px solid var(--dff-line);
  padding-top: 12px;
}

.dff-clause-negate {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dff-clause-negate input {
  width: auto;
  min-height: auto;
}

.dff-icon-button {
  min-height: 38px;
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 0 10px;
  background: var(--dff-surface);
  color: var(--dff-danger);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.dff-segment-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dff-segment-strip span,
.dff-empty-state {
  border-radius: var(--dff-radius);
  background: var(--dff-surface-muted);
  color: var(--dff-muted);
  padding: 8px 10px;
}

.dff-targeting-preview {
  position: sticky;
  top: 84px;
  display: grid;
  gap: 14px;
  padding: 18px;
}

.dff-preview-result {
  border: 1px solid var(--dff-line);
  border-radius: var(--dff-radius);
  padding: 12px;
  background: var(--dff-surface-muted);
}

.dff-preview-result dl {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 8px 12px;
  margin: 0;
}
```

- [ ] **Step 7: Run Targeting rendering and workflow tests**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py::test_flag_detail_renders_modern_targeting_workspace tests/test_dashboard_workflows.py::test_staff_can_save_targeting_document_from_flag_detail tests/test_dashboard_workflows.py::test_targeting_save_creates_approval_request_for_protected_environment -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/django_feature_flags/templates/django_feature_flags/flag_detail.html src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat(dashboard): redesign targeting workspace"
```

---

### Task 5: Add Sticky Unsaved-Changes Behavior

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/targeting.js`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Add a static save-bar test**

Append this test to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_targeting_workspace_has_unsaved_change_save_bar(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert 'data-targeting-form' in content
    assert 'data-save-bar' in content
    assert 'data-dirty-count' in content
    assert "Unsaved changes" in content
    assert "Save targeting" in content
```

- [ ] **Step 2: Add the sticky save bar markup**

In `flag_detail.html`, replace the existing final `.dff-form-actions.dff-targeting-actions` block with:

```html
<div class="dff-save-bar" data-save-bar>
  <div>
    <strong>Unsaved changes</strong>
    <span><span data-dirty-count>0</span> sections changed</span>
  </div>
  <label class="dff-field dff-save-reason" for="change-reason">
    <span>Change reason</span>
    <textarea id="change-reason" name="reason" rows="2"></textarea>
  </label>
  <div class="dff-actions">
    <a class="dff-button dff-button-secondary" href="{{ request.path }}?environment={{ state.environment.key }}">Discard</a>
    <button class="dff-button dff-button-primary" type="submit">Save targeting</button>
  </div>
</div>
```

Remove the earlier duplicate `change-reason` field from `.dff-targeting-final` so the `reason` field appears once.

- [ ] **Step 3: Replace `targeting.js` with add/remove plus dirty tracking**

Replace `src/django_feature_flags/static/django_feature_flags/targeting.js` with:

```javascript
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
```

- [ ] **Step 4: Add save-bar CSS**

Append to `dashboard.css`:

```css
.dff-save-bar {
  position: sticky;
  bottom: 16px;
  z-index: 8;
  display: grid;
  grid-template-columns: minmax(160px, 1fr) minmax(220px, 420px) max-content;
  gap: 12px;
  align-items: end;
  margin: 18px;
  border: 1px solid var(--dff-line-strong);
  border-radius: var(--dff-radius);
  padding: 12px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--dff-shadow);
}

.dff-save-bar strong,
.dff-save-bar span {
  display: block;
}

.dff-save-bar span {
  color: var(--dff-muted);
  font-size: 12px;
}

.dff-save-reason textarea {
  min-height: 42px;
}

.dff-targeting-layout:not(.dff-is-dirty) .dff-save-bar {
  border-color: var(--dff-line);
}

.dff-section-dirty {
  background: linear-gradient(90deg, rgba(49, 92, 246, 0.05), transparent 32%);
}
```

- [ ] **Step 5: Run save bar and dashboard workflow tests**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py::test_targeting_workspace_has_unsaved_change_save_bar tests/test_dashboard_workflows.py::test_staff_can_save_targeting_document_from_flag_detail -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_dashboard.py src/django_feature_flags/templates/django_feature_flags/flag_detail.html src/django_feature_flags/static/django_feature_flags/targeting.js src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat(dashboard): track targeting draft changes"
```

---

### Task 6: Add Responsive Polish And Final Verification

**Files:**
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`
- Test: `tests/test_dashboard_workflows.py`

- [ ] **Step 1: Add responsive CSS**

Append to `dashboard.css`:

```css
@media (max-width: 1100px) {
  .dff-app-shell {
    grid-template-columns: 210px minmax(0, 1fr);
  }

  .dff-topbar {
    grid-template-columns: 1fr 1fr;
  }

  .dff-search {
    grid-column: 1 / -1;
  }

  .dff-dashboard-grid,
  .dff-targeting-layout {
    grid-template-columns: 1fr;
  }

  .dff-targeting-preview {
    position: static;
  }

  .dff-targeting-state {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 760px) {
  .dff-app-shell {
    display: block;
  }

  .dff-sidebar {
    position: static;
    height: auto;
    border-right: 0;
    border-bottom: 1px solid var(--dff-line);
  }

  .dff-sidebar-nav {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dff-topbar {
    position: static;
    grid-template-columns: 1fr;
    padding: 12px 16px;
  }

  .dff-main {
    padding: 18px 16px 88px;
  }

  .dff-page-header,
  .dff-section-header {
    display: grid;
  }

  .dff-metric-grid {
    grid-template-columns: 1fr 1fr;
  }

  .dff-panel-flush {
    overflow-x: auto;
  }

  .dff-table {
    min-width: 720px;
  }

  .dff-targeting-state,
  .dff-builder-row,
  .dff-builder-row-wide,
  .dff-rule-topline,
  .dff-clause-row,
  .dff-save-bar {
    grid-template-columns: 1fr;
  }

  .dff-save-bar {
    left: 12px;
    right: 12px;
    bottom: 12px;
    margin: 12px 0 0;
  }
}

@media (max-width: 520px) {
  .dff-sidebar-nav,
  .dff-metric-grid {
    grid-template-columns: 1fr;
  }

  .dff-tabbar {
    overflow-x: auto;
  }
}
```

- [ ] **Step 2: Run focused dashboard tests**

Run:

```bash
python3.10 -m pytest tests/test_dashboard.py tests/test_dashboard_workflows.py -q
```

Expected: PASS.

- [ ] **Step 3: Run full automated verification**

Run:

```bash
python3.10 -m pytest -q
PYTHONPATH=src python3.10 -m django check --settings tests.settings
```

Expected: pytest reports all tests passing and Django reports no system check issues.

- [ ] **Step 4: Browser verification with local dev server**

Start the dev server:

```bash
PYTHONPATH=src python3.10 -m django runserver 127.0.0.1:8000 --settings tests.settings
```

Open these URLs while logged in as a staff user in the test/dev environment:

```text
http://127.0.0.1:8000/flags/
http://127.0.0.1:8000/flags/flags/
http://127.0.0.1:8000/flags/flags/<flag-id>/
```

Verify:

- overview is light, table-driven, and no longer says `Release Observatory`
- flag list has stable columns and no text overlap at desktop width
- Targeting has left workflow plus preview panel at desktop width
- add/remove prerequisite, target, and rule buttons still work
- changing any targeting field updates the unsaved changes count
- mobile width stacks sidebar, top bar, rules, preview, and save bar without overlap

- [ ] **Step 5: Commit**

```bash
git add src/django_feature_flags/static/django_feature_flags/dashboard.css
git commit -m "feat(dashboard): polish responsive console layout"
```

---

## Final Acceptance Run

After all tasks are complete, run:

```bash
git status --short
python3.10 -m pytest -q
PYTHONPATH=src python3.10 -m django check --settings tests.settings
```

Expected:

- `git status --short` shows no unstaged implementation changes after the final commit
- all pytest tests pass
- Django system check reports no issues

The completed redesign satisfies the approved spec when:

- the dashboard no longer renders observatory/cockpit copy or radar/timeline UI
- the base shell renders a light LaunchDarkly-style console with left navigation and top context bar
- overview and flag list are table-first operational pages
- flag detail has Targeting, Variations, Settings, and History tabs
- Targeting sections are ordered as targeting state/off variation, prerequisites, individual targets, segment rules, custom rules, default rule, preview, and save
- existing targeting save, approval, and preview workflows still pass tests
- no LaunchDarkly logo, brand copy, or exact pixel reproduction is introduced
