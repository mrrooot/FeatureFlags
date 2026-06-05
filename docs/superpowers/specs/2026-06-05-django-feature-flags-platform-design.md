# Django Feature Flags Platform Design

## Purpose

Build an installable Django package that gives a host Django application a full embedded feature flag platform similar in ambition to LaunchDarkly. The package owns its database tables through Django migrations, exposes a premium staff-only dashboard, evaluates flags locally inside the host app, and exposes remote SDK API endpoints for external services.

The package is intentionally a single integrated product rather than a separate control-plane service. A Django app can install it, run migrations, mount its URLs, and manage flags, experiments, analytics, and audit history from the dashboard.

## Product Scope

The package will include:

- multiple projects and environments
- global flag definitions shared across environments
- per-environment flag state
- boolean, string, number, and JSON variations
- targeting rules, segments, prerequisites, and percentage rollouts
- local Python/Django evaluation API
- remote SDK evaluation API with environment-specific SDK keys
- premium staff/admin dashboard
- evaluation, impression, conversion, and custom event capture
- advanced experiments with metrics, funnels, guardrails, holdouts, and result snapshots
- approval workflows, audit logs, change reasons, and production safety controls

The first design target is a full platform package. Internally, the code must still be modular so the dashboard, evaluator, events, experiments, and API layers do not become one tangled Django app.

## Installation Model

Expected host-app setup:

```python
INSTALLED_APPS = [
    # ...
    "django_feature_flags",
]
```

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("flags/", include("django_feature_flags.urls")),
]
```

Expected setup commands:

```bash
python manage.py migrate
python manage.py featureflags bootstrap
```

The bootstrap command creates the first project, common environments, and initial SDK keys. The package uses the host app's Django database and authentication system.

## Architecture

Main package modules:

- `core`: projects, environments, flags, variations, SDK keys, package settings
- `targeting`: rules, segments, prerequisites, context matching, rollout hashing
- `evaluation`: shared evaluator used by local Python calls and remote API calls
- `dashboard`: staff-only Django views, forms, templates, static assets, charts
- `api`: remote SDK endpoints and API authentication
- `events`: event ingestion, event storage, event aggregation
- `experiments`: experiment setup, allocation, metrics, analysis, result snapshots
- `audit`: change history, before/after payloads, approval workflows
- `management`: bootstrap, export, import, cleanup, key rotation commands

The evaluator is the behavioral source of truth. Dashboard previews, local evaluation, and remote API evaluation must all call the same evaluation engine.

## Environment Model

The package supports multiple projects and multiple environments inside one Django installation.

Flags are not duplicated per environment. A project has one global flag definition:

```text
Project
  FeatureFlag: new_checkout
    key, name, description, type, variations, rules, experiment definition

  Environment: development
    FlagState for new_checkout

  Environment: staging
    FlagState for new_checkout

  Environment: production
    FlagState for new_checkout
```

Shared globally:

- flag key, name, description, and type
- variations
- targeting rule definitions
- segment definitions
- experiment definitions
- metrics, funnels, and guardrails

Per environment:

- enabled or disabled state
- default variation
- rollout allocation
- experiment running, paused, or stopped state
- SDK keys
- events
- analytics result snapshots
- emergency overrides
- approval requirements

Creating a flag once makes it visible in every environment for that project. Environment-specific runtime behavior remains separate.

If staging and production are separate deployed Django apps with separate databases, the package cannot share state automatically through this model alone. The supported path for separate databases is export/import of portable flag configuration without secrets. The primary design assumes one Django installation manages multiple environments in the same database.

## Data Model

Core models:

- `Project`: product or app being managed
- `Environment`: named environment linked to a project
- `FeatureFlag`: global flag definition
- `Variation`: typed variation value for a flag
- `FlagState`: per-environment enabled state, default variation, rollout state, and overrides
- `Segment`: reusable audience group scoped to a project
- `SegmentRule`: segment membership rule definition
- `TargetingRule`: ordered flag targeting rule
- `SDKKey`: environment-specific key for remote evaluation and event ingestion
- `AuditLog`: who changed what, before/after payloads, reason, timestamp
- `ApprovalRequest`: proposed change, reviewer decision, and status
- `Event`: evaluation, impression, conversion, or custom event
- `Metric`: metric definition used by experiments
- `Experiment`: experiment definition linked to a flag
- `ExperimentAllocation`: variations, weights, holdouts, and audience split
- `ExperimentResultSnapshot`: stored experiment analysis summary

Rules and conditions use structured JSON payloads plus relational ownership fields. The package will keep database queries Django ORM-compatible and avoid relying on PostgreSQL-only behavior in the core path.

## Evaluation Behavior

Local evaluation example:

```python
from django_feature_flags import flags

enabled = flags.bool_variation(
    "new_checkout",
    context={"key": "user-123", "plan": "pro"},
    default=False,
    environment="production",
)
```

Remote evaluation example:

```http
POST /flags/api/evaluate/
Authorization: Bearer <sdk_key>
Content-Type: application/json

{
  "flag_key": "new_checkout",
  "context": {
    "kind": "user",
    "key": "user-123",
    "plan": "pro"
  },
  "default": false
}
```

The evaluator supports:

- multi-kind contexts such as user, organization, and device
- equality, inequality, contains, in-list, regex, numeric, date, and semantic version operators
- segments
- prerequisites
- percentage rollouts with stable hashing
- experiment allocation and holdouts
- typed default values
- safe fallback when a flag is missing, disabled, or invalid

Evaluation order:

1. validate project, environment, SDK key, and flag
2. return caller default if the flag is missing or archived
3. return environment default if the flag is disabled
4. apply emergency override when present
5. evaluate prerequisites
6. evaluate ordered targeting rules
7. evaluate experiment allocation when active
8. evaluate rollout allocation
9. return environment default variation
10. record evaluation or impression event when tracking is enabled

## Dashboard UX

The dashboard style direction is Premium SaaS: polished, clean, modern, and production-ready. It will feel beautiful without becoming a marketing page.

Core layout:

- left navigation: Overview, Flags, Segments, Experiments, Metrics, Approvals, Audit
- top project and environment switcher
- flag table with status, rollout, rules, experiment link, last changed, owner, and risk state
- side panels for experiment health, pending approvals, recent changes, and alerts
- detail pages with tabs instead of long scrolling forms

Flag detail tabs:

- Overview
- Targeting
- Variations
- Environments
- Experiment
- Metrics
- Audit

Experiment screens:

- allocation setup
- audience targeting
- primary and secondary metrics
- guardrails
- funnel steps
- schedule
- result analysis
- winner recommendation

The UI will use dense but readable tables, crisp typography, restrained color, clear status badges, chart panels, staff-friendly forms, and strong hover/focus states.

## Experiments And Analytics

Experiment features:

- multiple variations linked to a feature flag
- traffic allocation by percentage
- holdout groups
- primary metric
- secondary metrics
- guardrail metrics
- funnel metrics
- scheduled start and end
- pause, resume, stop
- winner recommendation
- result snapshots

Event types:

- evaluation event
- impression event
- conversion event
- custom event

Analytics views:

- exposures by variation
- conversions by variation
- conversion rate
- lift against control
- funnel step completion
- guardrail health
- time-series event trends
- experiment result summary

The first analytics implementation must be portable across Django-supported databases. Optional database-specific acceleration can be added in a future version without changing the public API.

## Permissions And Safety

The package uses the host app's Django auth. Dashboard access is restricted to staff/admin users by default.

Safety behavior:

- missing flags return the caller's default
- disabled flags return the environment default variation
- invalid rules are skipped, logged, and surfaced in the dashboard
- invalid SDK keys return unauthorized
- archived flags stop evaluating but remain visible in history
- emergency overrides can quickly disable or force a variation in one environment
- SDK keys can be rotated without deleting historical events

Production controls:

- optional approval requirements per environment
- optional required change reason
- before/after audit log for every dashboard change
- approval requests for high-risk changes
- dashboard warnings for active experiments, high rollout percentages, and production edits

## Management Commands

Commands:

- `featureflags bootstrap`: create initial project, environments, and SDK keys
- `featureflags create-environment`: add an environment to a project
- `featureflags rotate-key`: rotate an SDK key
- `featureflags export`: export portable flag configuration without secrets
- `featureflags import`: import portable flag configuration
- `featureflags cleanup-events`: prune or archive old event data
- `featureflags snapshot-results`: compute experiment result snapshots

Exports must not include SDK keys, secrets, or raw runtime events unless explicitly requested with a privileged option.

## Testing Strategy

Test areas:

- evaluation engine unit tests
- targeting operator tests
- segment and prerequisite tests
- percentage rollout determinism tests
- experiment allocation tests
- event capture tests
- analytics aggregation tests
- model and migration tests
- dashboard permission tests
- API authentication and response tests
- audit log tests
- approval workflow tests
- management command tests
- template and visual regression checks for key dashboard pages

The test project will run with SQLite for fast local compatibility checks. Database-specific behavior must be isolated behind optional tests.

## Non-Goals

The package will not require a separate external service for the primary use case. It will not require direct database access from external SDKs. It will not copy SDK keys between environments. It will not make PostgreSQL mandatory for the core package.

## Resolved Decisions

- Framework: Django
- Auth: host app Django staff/admin auth
- Scope: full big platform package
- Database target: any Django-supported database through ORM-compatible core behavior
- Projects/environments: multiple projects and environments
- Environment model: one global flag definition with per-environment state
- Evaluation access: both local Python evaluation and remote SDK API
- Dashboard direction: Hybrid Control Center structure with Premium SaaS polish
- Experiments: advanced experiments with metrics, guardrails, funnels, holdouts, and result snapshots
