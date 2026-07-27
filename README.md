# django-featureflags

Embedded feature flag management for Django projects.

`django-featureflags` gives you a staff dashboard, local flag evaluation, remote evaluation API, targeting rules, segments, experiments, events, approvals, audit logs, and management commands without running a separate feature flag service.

## Requirements

- Python 3.10+
- Django 4.2 through 5.x

## Install

```bash
pip install django-featureflags
```

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_feature_flags",
]
```

Add the package URLs:

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("flags/", include("django_feature_flags.urls")),
]
```

Run migrations:

```bash
python manage.py migrate
```

Bootstrap your first project, environments, and SDK keys:

```bash
python manage.py featureflags bootstrap --project ecommerce --name Ecommerce
```

The bootstrap command prints newly created SDK secrets once. Store them securely.

## Configuration

### Environments

Configure dashboard/bootstrap environments from Django settings:

```python
DJANGO_FEATURE_FLAGS_ENVIRONMENTS = ("development", "staging", "production")
```

Or from `.env` / process environment:

```env
DJANGO_FEATURE_FLAGS_ENVIRONMENTS=development,staging,production
```

If unset, the default environments are `development`, `staging`, and `production`.

### Branding

The dashboard brand can be configured from Django settings or environment variables. Django settings take precedence.

```env
DJANGO_FEATURE_FLAGS_BRAND_NAME=Thiqal
DJANGO_FEATURE_FLAGS_BRAND_MARK=TQ
DJANGO_FEATURE_FLAGS_BRAND_TAGLINE=Feature flag console
DJANGO_FEATURE_FLAGS_BRAND_TITLE=Thiqal Feature Flags
```

Defaults:

| Setting | Default | Used for |
| --- | --- | --- |
| `DJANGO_FEATURE_FLAGS_BRAND_NAME` | `Thiqal` | Sidebar brand name |
| `DJANGO_FEATURE_FLAGS_BRAND_MARK` | `TQ` | Sidebar and form rail mark |
| `DJANGO_FEATURE_FLAGS_BRAND_TAGLINE` | `Feature flag console` | Sidebar subtitle |
| `DJANGO_FEATURE_FLAGS_BRAND_TITLE` | `Thiqal Feature Flags` | Browser title |

## Dashboard Usage

Staff users can open:

```text
/flags/
```

The dashboard uses Django staff authentication. Users must be authenticated with `is_staff=True`.

Dashboard routes:

| Route | Purpose |
| --- | --- |
| `/flags/` | Overview |
| `/flags/flags/` | Feature flag list |
| `/flags/flags/new/` | Create flag |
| `/flags/flags/<id>/` | Flag detail and targeting |
| `/flags/flags/<id>/edit/` | Flag settings |
| `/flags/segments/` | Segments |
| `/flags/experiments/` | Experiments |
| `/flags/approvals/` | Approval requests |
| `/flags/audit/` | Audit log |

## Console UI

The dashboard UI is designed as a feature release control center for Django teams. It emphasizes safe releases, environment awareness, auditability, and fast operational scanning rather than a Django admin-style table skin.

Main screens:

- Overview: KPI cards, environment signal, recently changed flags, review queue, quick actions, and recent audit activity.
- Feature flags: searchable rollout board with operational flag rows, environment lanes, rollout exposure, status filters, and quick targeting access.
- Flag detail: control center for one flag with environment lanes, release safety context, targeting rules, evaluation preview, and SDK snippets.
- Segments: reusable audience rules for targeting and exclusions.
- Approvals: release safety queue for protected environment changes.
- Audit trail: searchable timeline of flag, approval, segment, and experiment changes with before/after detail.

Frontend architecture:

- No npm, no build step, no external CDNs, and no remote fonts.
- Templates live in `src/django_feature_flags/templates/django_feature_flags/`.
- Static CSS and browser-native JavaScript live in `src/django_feature_flags/static/django_feature_flags/`.
- The UI uses Django-rendered HTML, CSS design tokens, and small vanilla JavaScript enhancements for copy actions, toasts, theme toggle, command search focus, and form interaction hooks.
- Primary screens expose `data-dff-screen` and `data-dff-visual-checkpoint` attributes so no-dependency Django smoke tests, or future browser screenshot tests, can target stable UI landmarks.

Accessibility and security notes:

- The shell includes semantic landmarks, a skip link, active navigation state, visible focus rings, labeled form controls, `aria-live` toast messaging, and reduced-motion handling.
- User and database content is rendered through Django template escaping by default.
- Audit JSON is shown as escaped text and exposed with Django's `json_script` helper for safe machine-readable payloads.
- The frontend avoids `eval`, the `Function` constructor, external scripts/styles, and unsafe dynamic HTML injection.

Theming:

- The stylesheet defines tokens for backgrounds, surfaces, borders, text, accents, environments, flag states, approval/risk states, radii, shadows, spacing, z-index, animation timing, and focus rings.
- Light theme is the default. A dark theme token set is included and can be toggled in the dashboard without storing secrets or SDK keys.

## Create a Flag

Open:

```text
/flags/flags/new/
```

When a flag is created:

1. A `FeatureFlag` is created for the selected project.
2. A default `Variation` is created from the submitted default value.
3. Configured environments are synced for the project.
4. A disabled `FlagState` is created for each configured environment.

New flags are safe by default. They are not enabled in any environment until you turn targeting on.

## Local Evaluation

Use local evaluation when your Django app reads flags from the same database.

```python
from django_feature_flags import flags

enabled = flags.bool_variation(
    "new_checkout",
    {"key": "user-123", "plan": "pro"},
    default=False,
    project="ecommerce",
    environment="production",
)
```

Available helpers:

```python
flags.variation(flag_key, context, default=None, project="default", environment="production", track=False)
flags.bool_variation(flag_key, context, default=False, project="default", environment="production", track=False)
flags.string_variation(flag_key, context, default="", project="default", environment="production", track=False)
flags.number_variation(flag_key, context, default=0, project="default", environment="production", track=False)
flags.json_variation(flag_key, context, default=None, project="default", environment="production", track=False)
```

Set `track=True` to record evaluation events.

## Caching & Database Cost

Every evaluation needs configuration data — the flag, its variations, the
environment's flag state, the targeting document, targeting rules, any running
experiment, and referenced segments. Read straight from the database that is
roughly a dozen queries per flag check (targeting validation alone runs four).

To remove that from the hot path, evaluation reads from a cached, immutable
**config snapshot** built once per `(project, environment)` and stored in
Django's cache framework. On a cache hit, evaluating any flag in that
environment issues **zero database queries** (a `track=True` write is the only
exception — one insert). A representative flag with a segment rule:

| | 50 evaluations |
| --- | --- |
| Uncached | ~450 queries |
| Cached (steady state) | 0 queries |

The first evaluation after a change pays a single small build (~8–10 queries)
that then serves every flag in the environment until the next write.

### Invalidation

Any write to a config model (flag, variation, flag state, targeting rule,
segment, experiment, …) invalidates every cached snapshot immediately via
Django signals. A TTL bounds staleness as a backstop — this matters in two
cases:

- **Per-process caches** (the default `LocMemCache`): a write in one worker
  can't reach another worker's memory, so other workers refresh within the TTL.
  Point the cache alias at a **shared backend (Redis/Memcached)** for instant
  cross-process invalidation.
- **Bulk writes** that bypass signals (`QuerySet.update()`, `bulk_create()`):
  these refresh within the TTL. Call
  `django_feature_flags.evaluation.config.bump_generation()` to invalidate
  immediately.

### Settings

| Setting | Default | Purpose |
| --- | --- | --- |
| `DJANGO_FEATURE_FLAGS_CACHE_ENABLED` | `True` | Turn the config cache on/off. When off, behavior is identical but every evaluation reads the database. |
| `DJANGO_FEATURE_FLAGS_CACHE_ALIAS` | `"default"` | Which `CACHES` alias to use. Use a shared backend in production. |
| `DJANGO_FEATURE_FLAGS_CACHE_TTL` | `300` | Snapshot lifetime in seconds (staleness backstop). |

```python
# settings.py
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "feature_flags": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    },
}
DJANGO_FEATURE_FLAGS_CACHE_ALIAS = "feature_flags"
DJANGO_FEATURE_FLAGS_CACHE_TTL = 300
```

The dashboard targeting **preview** always evaluates against live, unsaved edits
and bypasses the cache.

## Remote Evaluation API

Remote callers can evaluate flags with an SDK key.

```http
POST /flags/api/evaluate/
Authorization: Bearer <sdk_key>
Content-Type: application/json

{
  "flag_key": "new_checkout",
  "context": {"key": "user-123", "plan": "pro"},
  "default": false,
  "track": true
}
```

Example response:

```json
{
  "value": true,
  "variation_key": "default",
  "reason": "fallthrough",
  "flag_key": "new_checkout",
  "environment_key": "production"
}
```

Errors:

```json
{"error": "unauthorized"}
```

```json
{"error": "invalid_json"}
```

## Targeting

Open a flag detail page from `/flags/flags/` and use the Targeting workspace.

Supported targeting controls:

- targeting on/off
- off variation
- prerequisites
- individual targets
- segment rules
- custom rules
- default/fallthrough rule
- rollout serving
- event tracking
- preview evaluation
- approval-aware saves

Example preview context:

```json
{
  "user": {"key": "user-123", "plan": "pro"},
  "device": {"key": "phone-1", "platform": "ios"},
  "organization": {"key": "org-9", "tier": "enterprise"}
}
```

## Management Commands

```bash
python manage.py featureflags bootstrap --project ecommerce --name Ecommerce
```

Creates a project, configured environments, and SDK keys.

```bash
python manage.py featureflags rotate-key --project ecommerce --environment production
```

Deactivates active SDK keys for an environment and prints a new secret.

```bash
python manage.py featureflags export --project ecommerce > flags-export.json
```

Exports project flag configuration.

```bash
python manage.py featureflags import flags-export.json
```

Imports project flag configuration.

```bash
python manage.py featureflags cleanup-events --days 90
```

Deletes old events.

```bash
python manage.py featureflags snapshot-results
```

Creates experiment result snapshots.

## Security Notes

- Keep SDK secrets private.
- Use HTTPS for remote evaluation in production.
- Rotate SDK keys if a secret is exposed.
- Use approval requirements for protected environments.
- Keep dashboard access limited to trusted staff users.

## Development

Install locally with test dependencies:

```bash
python -m pip install -e ".[test]"
```

Run tests:

```bash
pytest -q
```

Run dashboard tests:

```bash
pytest tests/test_dashboard.py -q
```

Check dashboard JavaScript:

```bash
node --check src/django_feature_flags/static/django_feature_flags/dashboard.js
```

## Version

```text
0.2.0
```
