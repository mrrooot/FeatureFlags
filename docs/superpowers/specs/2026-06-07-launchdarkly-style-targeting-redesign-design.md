# LaunchDarkly-Style Targeting Redesign

## Purpose

Redesign flag control around a dashboard-first, LaunchDarkly-style Targeting tab. Staff users should be able to control who receives each variation by environment, context kind, segment, platform/device attribute, custom rule, rollout, and default behavior without writing JSON.

This is a functional targeting redesign, not a dashboard-only visual pass. The data model, evaluator, dashboard, validation, audit behavior, and tests must move together.

## Scope

This spec covers the first implementation slice:

- a flag detail page with a single Targeting tab
- environment-specific targeting controls
- on/off targeting state
- off variation
- prerequisites
- individual targets across context kinds
- reusable segment targeting
- custom rules with multi-context clauses
- fixed variation and weighted rollout serve behavior
- fallthrough/default rule
- preview evaluation with explanation
- evaluator updates for the new targeting document
- validation, audit, approvals, and tests

This spec does not clone the full LaunchDarkly management API. The dashboard is the primary control surface. The existing evaluation API can continue to evaluate flags, but management API parity is a later project.

## Product References

The design follows these LaunchDarkly concepts:

- each flag has a Targeting tab with prerequisites, individual targets, targeting rules, and a default rule
- contexts can represent users, devices, organizations, services, or other resources
- multi-context evaluation can use data from several context kinds at once
- targeting rules have conditions and a rollout
- segment targeting lets many flags reuse the same audience definition
- off variation and fallthrough/default rule are distinct behaviors
- percentage rollout weights are represented on a 0 to 100000 scale

Reference docs:

- https://launchdarkly.com/docs/home/flags/target
- https://launchdarkly.com/docs/home/flags/target-rules
- https://launchdarkly.com/docs/home/flags/segment-targeting
- https://launchdarkly.com/docs/home/flags/multi-contexts
- https://launchdarkly.com/docs/guides/flags/flag-hierarchy
- https://launchdarkly.com/docs/api/feature-flags

## Current State

The package already has:

- `Project`, `Environment`, `FeatureFlag`, `Variation`, `FlagState`, `Segment`, `SegmentRule`, and `TargetingRule` models
- local and remote evaluation through `django_feature_flags.evaluation.evaluator.evaluate`
- a staff dashboard with flag list, create, and update views
- basic targeting operators and percentage rollout hashing
- segments, experiments, approvals, audit logs, and events

Current gaps:

- flag editing only covers identity and default value
- there is no flag detail page or Targeting tab
- `TargetingRule` is global to a flag instead of scoped to an environment
- multi-context targeting is only partially supported through nested lookup by attribute path
- dashboard users must rely on JSON-heavy segment and experiment forms for advanced behavior
- evaluator order does not match LaunchDarkly-style targeting flow

## UX Design

The flag ledger's `Edit flag` action should lead to a richer flag detail page. The page has tabs or tab-like sections:

- Targeting
- Variations
- Environments
- Audit
- Settings

The first implementation focuses on the Targeting tab. The existing `flag_form.html` can remain available for identity/default editing, but the normal workflow should be the flag detail page.

The Targeting tab uses a single stacked layout, selected during brainstorming:

1. environment selector
2. targeting on/off toggle
3. off variation selector
4. prerequisites
5. individual targets
6. segment targeting and custom rules
7. default rule
8. preview evaluator
9. review and save

The UI should not expose raw targeting JSON for normal control. Staff users should use form rows, dropdowns, rule cards, and add/remove controls. JSON is acceptable only for the preview context input and optional debug display.

## Data Model

Add a `targeting` JSON field to `FlagState`.

Existing fields remain for compatibility:

- `enabled` remains the primary on/off state
- `default_variation` remains the safe fallback
- `rollout` and `emergency_override` continue to be read while migration compatibility is needed

Targeting document shape:

```json
{
  "off_variation": "default",
  "prerequisites": [
    {"flag_key": "account_ready", "variation_key": "enabled"}
  ],
  "targets": [
    {
      "context_kind": "user",
      "variation_key": "enabled",
      "values": ["user-123", "user-456"]
    }
  ],
  "rules": [
    {
      "id": "rule-1",
      "description": "iOS beta customers",
      "clauses": [
        {
          "context_kind": "device",
          "attribute": "platform",
          "operator": "in",
          "values": ["ios", "android"],
          "negate": false
        },
        {
          "context_kind": "user",
          "attribute": "segment",
          "operator": "segment_match",
          "values": ["beta_users"],
          "negate": false
        }
      ],
      "serve": {"variation_key": "enabled"}
    }
  ],
  "fallthrough": {"variation_key": "default"},
  "track_events": false
}
```

Rollout serve behavior uses this shape:

```json
{
  "rollout": {
    "context_kind": "user",
    "salt": "optional-stable-salt",
    "variations": [
      {"variation_key": "control", "weight": 50000},
      {"variation_key": "enabled", "weight": 50000}
    ]
  }
}
```

Weights must total `100000`.

## Targeting Service

Create a targeting service module that is the only layer allowed to normalize and validate targeting documents. Views and evaluator should not manipulate raw JSON directly.

Responsibilities:

- build an empty/default targeting document for a `FlagState`
- migrate legacy `default_variation` and `rollout` fields into a normalized read model
- validate submitted targeting documents
- resolve variation keys to `Variation` objects
- resolve prerequisite flags
- resolve segment keys
- detect circular prerequisites
- apply dashboard form submissions into normalized targeting documents
- return structured validation errors keyed by section

This service should keep JSON flexible while giving the rest of the code typed helper functions and predictable errors.

## Evaluation Behavior

Evaluation order:

1. return caller default if project, environment, flag, or state is missing
2. apply `emergency_override` if it points to a valid variation
3. if `enabled` is false, serve `targeting.off_variation`, then `default_variation`, then caller default
4. evaluate prerequisites; if any prerequisite is off or returns the wrong variation, serve the dependent flag's off/default behavior safely
5. evaluate individual targets grouped by context kind and variation
6. evaluate ordered targeting rules
7. for each rule, require all clauses to match
8. when a rule matches, serve a fixed variation or weighted rollout
9. if no rule matches, serve fallthrough/default
10. record events with richer reason metadata when tracking is enabled

Preferred multi-context input:

```json
{
  "user": {"key": "user-123", "plan": "pro"},
  "device": {"key": "iphone-1", "platform": "ios", "app_version": "2.4.0"},
  "organization": {"key": "org-9", "tier": "enterprise"}
}
```

Flat legacy contexts continue to work as a `user` context:

```json
{"key": "user-123", "plan": "pro"}
```

Evaluation reasons:

- `project_not_found`
- `environment_not_found`
- `flag_not_found`
- `state_not_found`
- `emergency_override`
- `off`
- `prerequisite_failed`
- `target_match`
- `rule_match`
- `fallthrough`
- `invalid_targeting`

## Dashboard Components

Keep the implementation mostly server-rendered Django. Add lightweight JavaScript only for dynamic add/remove interactions in the Targeting tab.

Sections:

- **Environment header:** environment selector, targeting toggle, status badge, save action
- **Off variation:** variation dropdown
- **Prerequisites:** rows of prerequisite flag plus expected variation
- **Individual targets:** context kind, variation, and newline/comma-separated keys
- **Rules:** ordered rule cards with description, clause builder, and serve behavior
- **Default rule:** fixed variation or weighted rollout
- **Preview:** textarea for context JSON and result summary

Rule clause fields:

- context kind
- attribute
- operator
- values
- negate

Initial operators:

- `equals`
- `not_equals`
- `in`
- `not_in`
- `contains`
- `matches`
- `greater_than`
- `greater_than_or_equal`
- `less_than`
- `less_than_or_equal`
- `before`
- `after`
- `segment_match`

## Preview

The preview panel evaluates a pasted context without saving changes.

It returns:

- flag key
- environment key
- value
- variation key
- reason
- matched rule id or target section when available
- validation errors for malformed context JSON

The preview should use the same evaluator path as production evaluation, with an option to pass an unsaved targeting document from the form.

## Validation And Safety

Validation rules:

- every referenced variation key must exist for the flag
- every prerequisite flag must exist in the same project
- prerequisite chains must not be circular
- individual target values must not be empty
- each rule must have at least one clause
- each clause must include `context_kind`, `attribute`, `operator`, and valid values
- rollout weights must total `100000`
- segment references must exist in the same project
- changes in any environment must honor that environment's `requires_approval` and `require_change_reason` settings

Error handling:

- invalid saved targeting documents fail closed by serving the default variation or caller default
- dashboard save errors preserve submitted values
- preview errors do not save anything
- evaluator errors use `invalid_targeting` rather than raising to callers

## Audit And Approvals

Targeting changes must create audit records with before/after targeting payloads and a useful action name, such as `flag.targeting.updated`.

For environments with `requires_approval`, saving targeting changes creates or updates an approval request instead of applying immediately. For environments with `require_change_reason`, the form requires a reason before saving or requesting approval.

## Compatibility And Migration

Migration adds `FlagState.targeting` with an empty dict default.

Read compatibility:

- if `targeting` is empty, derive off/default/fallthrough from `default_variation`
- if legacy `rollout` is present, expose it as fallthrough rollout in the normalized targeting read model
- when `targeting` is empty, existing global `TargetingRule` rows remain a read-only fallback for backward compatibility
- when `targeting` is non-empty, the evaluator ignores global `TargetingRule` rows for that flag/environment and uses the per-environment targeting document

Write behavior:

- new dashboard saves write to `FlagState.targeting`
- new per-environment rules should not create global `TargetingRule` rows

## Testing Strategy

Tests should cover:

- migration/model defaults for `FlagState.targeting`
- targeting document normalization
- validation failures and section-level errors
- multi-context attribute lookup
- individual targets by context kind
- segment matching
- prerequisites and circular prerequisite rejection
- fixed variation rule matching
- weighted rollout determinism
- off variation and fallthrough behavior
- invalid targeting fail-closed behavior
- dashboard page rendering
- dashboard save workflows for each section
- preview workflow
- audit creation
- approval behavior for protected environments
- backwards compatibility with existing flag evaluation defaults

## Non-Goals

- full LaunchDarkly management API clone
- progressive rollouts
- guarded rollouts
- experiments inside targeting rules
- big segments or external segment stores
- client-side SDK streaming
- code references
- role-based access controls beyond existing staff/admin behavior

These can be designed in later specs after dashboard targeting is working end to end.
