# LaunchDarkly-Style Modern Dashboard Redesign

## Purpose

Redesign the dashboard so it feels like a modern LaunchDarkly-style feature flag console: clean, light, dense, operational, and centered on the Targeting workflow.

The current dashboard is a dark "Release Observatory" concept. It is visually distinctive, but it does not match the user's requested product direction. The new design should feel closer to LaunchDarkly's enterprise SaaS interface while staying original to this project and avoiding a pixel-for-pixel copy of LaunchDarkly branding.

## Decision

Use a LaunchDarkly-style structure with a modernized visual system:

- light application shell
- persistent left navigation
- compact top context bar for project, environment, search, and primary actions
- table-first flag list
- flag detail page with tabs
- Targeting tab as the primary control workflow
- ordered rule sections for prerequisites, individual targets, segment rules, custom rules, default rule, and off variation
- rule cards that read like `IF context attribute operator value THEN serve variation`
- sticky review/save bar for pending changes
- restrained modern polish through spacing, borders, focus states, and subtle elevation

This is a dashboard redesign, not a LaunchDarkly management API clone and not a new targeting engine project.

## Product References

LaunchDarkly's targeting documentation confirms the core workflow this redesign should visually support:

- targeting rules live on a flag's Targeting tab
- each rule includes a description, one or more conditions, and rollout behavior
- contexts represent users, devices, organizations, services, and other entities
- flags can include prerequisites, individual targets, targeting rules, and a default rule
- segment rules let multiple flags reuse the same audience definition
- the save workflow should support reviewing targeting changes before committing them

Reference docs:

- https://launchdarkly.com/docs/home/flags/target
- https://launchdarkly.com/docs/home/flags/target-rules
- https://launchdarkly.com/docs/home/flags/segment-targeting

## Scope

This spec covers a visual and interaction redesign for the existing Django dashboard:

- base dashboard shell
- dashboard overview
- flag list
- flag detail header and tabs
- Targeting tab layout and controls
- rule builder visual treatment
- preview panel
- save/review change bar
- responsive behavior
- empty, error, disabled, hover, focus, and changed states

The implementation should remain server-rendered Django templates with static CSS and lightweight JavaScript. No frontend framework is introduced for this pass.

## Non-Goals

- Do not copy LaunchDarkly logos, brand marks, exact color tokens, or exact screen pixels.
- Do not add a full management API clone.
- Do not change evaluator semantics unless a UI state exposes an existing bug.
- Do not replace the server-rendered Django dashboard with React, Vue, or another SPA framework.
- Do not redesign public docs, SDK APIs, or backend models unless needed for rendering the approved UI states.

## Current State

The current dashboard includes:

- `base.html` with a permanent dark sidebar and "FeatureFlow / Release Observatory" branding
- `dashboard.html` with radar, command-map, timeline, and cockpit metaphors
- `flag_list.html` with a flag ledger table
- `flag_detail.html` with a working Targeting tab, environment selector, targeting toggle, prerequisites, individual targets, segment list, rules, default rule, tracking toggle, preview panel, and save action
- `dashboard.css` with a dark neon visual system, decorative gradients, grid texture, radar animation, serif display typography, and dense custom components
- `targeting.js` for adding/removing targeting rows client-side

The functional foundation is good. The redesign should preserve the working Targeting flow and replace the visual language.

## Experience Principles

1. Operational clarity comes first.
   Users should understand which flag, project, and environment they are editing before touching a rule.

2. Match LaunchDarkly's mental model.
   The UI should organize targeting by flag detail tabs and ordered targeting sections, not by abstract dashboard metaphors.

3. Dense, not cramped.
   Tables and rule builders should show enough data for scanning, with stable row heights, consistent labels, and predictable actions.

4. Modernized, not flashy.
   Use crisp cards, clear typography, subtle borders, restrained shadows, and purposeful accent color. Avoid decorative radar, grid, and cockpit motifs.

5. Safe change flow.
   Targeting edits should visually accumulate into a pending-change state and end in a deliberate review/save action.

## Information Architecture

### Application Shell

The shell keeps a persistent left navigation and adds a top context bar.

Left navigation:

- Feature flags
- Segments
- Experiments
- Approvals
- Audit log
- Settings

Top context bar:

- project selector or current project label
- environment selector
- search field
- documentation/API shortcut if available
- primary action button on list pages, such as `Create flag`

The sidebar should be quieter than the content area. It should use a light or near-white background, compact nav rows, clear active state, and small count badges when data is available.

### Dashboard Overview

The overview should stop using the command-center metaphor and become a product console summary:

- compact metric strip for projects, flags, segments, approvals, and recent changes
- "Recently updated flags" table
- "Needs review" list for approvals or risky changes
- "Quick actions" band for creating a flag, creating a segment, and opening audit log

The overview is useful, but it should not compete with the flag workflow. It should be calm and table-driven.

### Flag List

The flag list should be the main entry point.

Recommended columns:

- flag name and key
- project
- type
- environments
- targeting status
- tags or segment count if available
- last updated if available
- row action

Rows should use clear status pills:

- On
- Off
- Mixed
- Archived
- Needs review

The row action should say `Open` or use a compact icon/action menu. The primary call to action is `Create flag`.

### Flag Detail

The flag detail page should look like a LaunchDarkly-style flag workspace.

Header:

- flag name
- flag key in monospace
- enabled/off status
- project
- selected environment
- create/review/save actions as appropriate

Tabs:

- Targeting
- Variations
- Settings
- History

Only Targeting must be fully functional in this pass. Disabled or future tabs may remain visible only if they do not look broken. If they are not useful, keep only `Targeting` and `Settings`.

## Targeting Tab Design

The Targeting tab should become a single ordered workflow.

Recommended section order:

1. targeting state, environment, and off variation
2. prerequisites
3. individual targets
4. segment rules
5. custom rules
6. default rule
7. preview
8. review and save

Each section should be a clean content block with:

- title
- short helper text only when it clarifies risk or behavior
- add action
- empty state
- validation errors local to the section
- changed-state indicator when values have been edited

### Targeting State

Use a prominent but compact toggle for `Targeting on`.

When targeting is off:

- show the selected off variation
- visually dim rules that will not run
- keep rules editable unless the backend forbids it
- show a clear note that requests receive the off/default variation while targeting is off

### Prerequisites

Prerequisites should appear before user targeting because they gate the rest of the flag.

Each prerequisite row:

- required flag selector
- required variation key selector/input
- remove action

Validation states:

- missing flag
- missing variation
- prerequisite references current flag
- circular prerequisite if available from existing validation

### Individual Targets

Use grouped rows by context kind and variation:

- context kind input or selector
- variation selector
- context key list textarea
- remove action

The visual label should read like:

`Serve <variation> to <context kind> keys`

### Segment Rules

Segments should feel like reusable audiences, separate from generic custom clauses.

Segment rule block:

- rule name
- include/exclude operator
- segment selector or key input
- serve variation
- optional add condition if existing functionality supports it

Segment chips should show segment keys in a readable pill style. Empty state should point users to the Segments section.

### Custom Rules

Custom rules should be the richest area.

Each rule card:

- order grip or numeric order badge
- rule name
- `IF` clause stack
- `THEN` serve control
- remove action
- validation summary

Each clause row:

- context kind
- attribute
- operator
- values
- negate checkbox

The row should visually read left to right:

`IF [user] [email] [ends with] [.edu]`

All clauses in a rule are ANDed together. Multiple values inside a segment condition use OR behavior, matching LaunchDarkly's segment targeting concept.

### Default Rule

The default rule appears after all explicit rules.

It should read:

`If no targeting rules match, serve <variation>`

If weighted rollout support is already exposed, the same area can support fixed variation or weighted rollout. If not, keep the first pass as fixed variation.

### Off Variation

The off variation is distinct from the default rule.

It should read:

`When targeting is off, serve <variation>`

This control belongs near the top next to the targeting state so users understand disabled behavior before editing rules. It may be summarized again near the bottom, but the canonical editable control should appear once.

### Preview

The preview panel should remain available but become more integrated.

Desktop:

- sticky right panel or lower side panel with multi-context JSON input
- preview button
- result card with variation, reason, and value

Mobile:

- preview appears below targeting rules
- sticky behavior is disabled

Preview errors should be local to the preview panel and should not look like saved targeting validation errors.

### Review and Save

Use a sticky bottom bar when the form has unsaved changes.

Content:

- changed sections count or simple `Unsaved changes`
- optional change reason textarea when space allows
- `Discard` link/button if available
- `Review changes` primary button if a review route exists, otherwise `Save targeting`

For the current implementation, saving directly is acceptable. The visual design should leave room for a future review modal without requiring a rewrite.

## Visual System

### Theme

Use a light enterprise UI:

- background: cool off-white
- surfaces: white
- text: near-black navy/charcoal
- secondary text: blue-gray
- borders: soft gray
- accent: deep teal or indigo-blue
- success: green
- warning: amber
- danger: red

Avoid the current dark neon, radial gradients, cockpit grid, radar animation, and paper/serif mix.

### Typography

Use a modern UI stack already available locally:

- body: Aptos, Segoe UI, system UI fallback
- code/keys: Cascadia Code, SFMono-Regular, Consolas fallback

Do not use oversized hero typography inside operational pages. Headings should be compact and scannable.

### Components

Core reusable components:

- app shell
- sidebar nav item
- top bar
- page header
- tabs
- button variants
- icon button
- status pill
- chip
- panel/content block
- table
- form field
- toggle
- rule card
- clause row
- preview result
- sticky save bar
- alert/error message
- empty state

Border radius should stay at 8px or less. Buttons and inputs should have stable heights. Text inside buttons and chips must not overflow on small screens.

### Motion

Motion should be minimal:

- hover states
- focus rings
- subtle changed-state highlight
- smooth sticky save bar entrance

No decorative background animation.

## Data Flow

The redesign does not change core data flow:

1. Django views load projects, environments, flags, states, variations, segments, and targeting data.
2. Templates render forms using existing context.
3. `targeting.js` adds and removes form rows using templates.
4. Submitting targeting posts to the existing targeting view.
5. Preview posts to the existing preview route.
6. Validation errors return to the same page and are displayed near the affected section.

The redesign may add CSS classes, data attributes, and small JavaScript enhancements for changed-state tracking. Those enhancements must not be required for form submission to work.

## Error Handling

Errors should be visible where users can fix them:

- form-wide errors at the top only for unknown failures
- prerequisite errors inside the prerequisite section
- target errors inside individual target rows
- rule errors inside the relevant rule card
- preview JSON errors inside the preview panel
- save failures in the sticky save bar and top alert area

Do not rely only on color. Error states need text and accessible attributes where practical.

## Accessibility

The redesign must preserve:

- semantic form labels
- keyboard reachable controls
- visible focus rings
- table headers
- current-page tab/nav state
- aria labels for icon-only actions
- sufficient color contrast on status pills and alerts

The layout should work without JavaScript for existing rows. JavaScript-created rows should match the same label and input structure.

## Responsive Behavior

Desktop:

- fixed or sticky sidebar
- top context bar
- main content max width suitable for dense tables
- Targeting can use two columns with preview on the right

Tablet:

- sidebar may compact
- Targeting preview moves below or becomes non-sticky
- rule rows wrap at clear breakpoints

Mobile:

- sidebar becomes top navigation or collapses into a simple stacked nav
- tables become horizontally scrollable or use compact row cards
- rule cards stack controls vertically
- sticky save bar remains usable and does not cover form fields

## Implementation Boundaries

Likely files:

- `src/django_feature_flags/templates/django_feature_flags/base.html`
- `src/django_feature_flags/templates/django_feature_flags/dashboard.html`
- `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`
- `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- `src/django_feature_flags/static/django_feature_flags/targeting.js`

The first implementation should prefer CSS/template changes. View changes are allowed only when needed to render labels, active nav states, changed-state metadata, or future-safe review controls.

## Testing and Verification

Automated checks:

- existing Python test suite
- Django system check
- targeted dashboard view tests if template context or routes change

Manual/browser checks:

- dashboard overview renders
- flag list renders with empty and populated states
- flag detail Targeting tab renders with existing targeting data
- add/remove prerequisite, target, and rule controls still work
- targeting save still posts successfully
- preview still posts successfully
- errors remain visible after invalid submissions
- desktop and mobile widths do not overlap text or controls

If a local dev server is needed for browser verification, start it after implementation and provide the URL.

## Acceptance Criteria

- The dashboard no longer reads as a dark observatory/cockpit interface.
- The UI visibly matches the LaunchDarkly-style structure: left nav, context bar, tables, flag detail tabs, and rule-builder targeting.
- The Targeting tab remains fully functional.
- Existing targeting semantics are preserved.
- Forms and tables are readable on desktop and usable on mobile.
- There is no LaunchDarkly branding copy, logo copy, or exact pixel reproduction.
- Existing tests and Django checks pass after implementation.
