# Editorial Ledger Dashboard Redesign

## Summary

Redesign the Django Feature Flags dashboard as an **Editorial Ledger Workspace** across all current dashboard screens: overview, flags list, and create flag form.

The redesign should make the package feel premium and operational, with warm editorial polish, strong table hierarchy, refined forms, and fast scanning for admins managing feature flags. It remains a frontend-focused slice: no database, route, authentication, or flag-creation behavior changes.

## Goals

- Make the dashboard feel significantly more polished and product-ready.
- Keep the UI efficient for repeated admin workflows, not a marketing-style landing page.
- Redesign the overview, flags list, and create flag form as one cohesive system.
- Preserve the current Django template architecture and package install simplicity.
- Improve empty, validation, message, and responsive states.

## Non-Goals

- No model or migration changes.
- No route changes.
- No JavaScript build pipeline.
- No new runtime frontend dependencies.
- No changes to flag evaluation, SDK behavior, admin auth, or environment sync.
- No visual snapshot test harness in this slice.

## Visual Direction

The approved direction is **Editorial Ledger Workspace**.

The visual system should combine:

- A soft paper-gray background with subtle CSS texture.
- Deep navy/charcoal ink for navigation, headings, and table emphasis.
- Restrained copper accents for primary actions and important stamps.
- Muted teal for healthy or ready states.
- Thin rules, ledger-style dividers, stamped badges, and 8px panels.
- Serif-influenced display treatment for page-level headings where it improves the editorial tone.
- Sans-serif treatment for operational data, tables, buttons, and forms.

The palette must avoid becoming beige-heavy or one-note. Motion should stay minimal: hover transitions, focus rings, and small table/button feedback only.

## Screen Structure

### Overview

The overview becomes the command desk.

It should include:

- A refined editorial header with a strong title and concise operational subtitle.
- Compact KPI ledger cards for projects, flags, and release/experiment health.
- A recent flags section with improved table treatment.
- A side or companion panel for release posture, emphasizing that flags are controlled and reviewable.
- A clear "New flag" action without turning the page into a landing screen.

### Flags List

The flags list becomes the primary ledger.

It should include:

- A stronger page header and action area.
- A table optimized for scanning flag key, display name, project, type, environments, and status.
- Stamped status badges for archived, enabled, ready, and configured-off states.
- Environment chips that read cleanly without crowding the row.
- A designed empty state with a direct create action.

### Create Flag Form

The create flag form becomes a guided editorial form.

It should include:

- A polished form panel for project, key, name, type, description, default value, and environments.
- A companion guidance panel explaining default variation and disabled initial states.
- Field-level validation that remains close to the field and is visually clear.
- Clear primary and secondary actions.
- Responsive one-column behavior on smaller screens.

## Component Plan

Keep the existing Django template boundaries:

- `base.html`: shared sidebar, shell, global messages.
- `dashboard.html`: overview command desk, KPI cards, recent flags, release posture panel.
- `flag_list.html`: ledger table, environment chips, statuses, empty state.
- `flag_form.html`: create workflow, field groups, guidance panel.
- `dashboard.css`: shared tokens, layout primitives, buttons, tables, badges, forms, messages, responsive rules.

No new JavaScript is required.

## Template And Data Flow

Use the data already passed by the current dashboard views:

- Overview uses `project_count`, `flag_count`, `recent_flags`, and `style_name`.
- Flags list uses `flag_rows`, including each `flag`, its `states`, and `enabled_count`.
- Create form uses the existing `FeatureFlagCreateForm`.
- Messages continue through Django's messages framework in `base.html`.

Small view-level display values may be added only if needed for presentation, such as a label or aggregate count. They must not change persistence or business behavior.

## States And Responsiveness

The redesign should cover non-happy paths:

- Empty overview and list states have a designed callout and a "New flag" action.
- Form validation errors use high-contrast field-adjacent treatment.
- Success messages render as refined alert strips.
- Tables stay readable on mobile through horizontal overflow when needed.
- Forms collapse to one column on narrow screens.
- Buttons remain tap-friendly on mobile.
- Focus states are visible for keyboard users.

## Accessibility

- Keep one `h1` per page.
- Preserve logical heading order.
- Ensure labels stay associated with form fields.
- Use visible focus rings for links, buttons, inputs, selects, and textareas.
- Maintain readable contrast for muted text, badges, and buttons.
- Avoid hover-only cues for essential information.

## Testing And Verification

Verification must include:

- Existing dashboard tests for route protection, create form rendering, create behavior, and visible create action.
- Full `pytest` suite.
- `django check --settings=tests.settings`.
- `git diff --check`.

A browser visual pass should be attempted if a local preview can be reached cleanly. If the local preview setup is unreliable, record that honestly and rely on rendered template tests plus Django checks for this slice.

## Implementation Scope

Primary expected files:

- `src/django_feature_flags/templates/django_feature_flags/base.html`
- `src/django_feature_flags/templates/django_feature_flags/dashboard.html`
- `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- `src/django_feature_flags/templates/django_feature_flags/flag_form.html`
- `src/django_feature_flags/static/django_feature_flags/dashboard.css`

Tests may be updated only when visible template behavior changes.
