# django-featureflags

Embedded Django feature flag platform with local evaluation, remote SDK API, staff dashboard, events, experiments, audit logs, and management commands.

## Install

```bash
pip install django-featureflags
```

Add the app and URLs:

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

Run migrations and bootstrap:

```bash
python manage.py migrate
python manage.py featureflags bootstrap --project ecommerce --name Ecommerce
```

Configure dashboard/bootstrap environments from your project settings or `.env`:

```env
DJANGO_FEATURE_FLAGS_ENVIRONMENTS=development,staging,production
```

## Local Evaluation

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

## Remote Evaluation

```http
POST /flags/api/evaluate/
Authorization: Bearer <sdk_key>
Content-Type: application/json

{
  "flag_key": "new_checkout",
  "context": {"key": "user-123", "plan": "pro"},
  "default": false
}
```

## Dashboard

Staff users can open `/flags/` to manage the platform dashboard.

## Dashboard Targeting

Open `/flags/flags/`, choose a flag, and use the Targeting tab to configure one environment at a time. The dashboard supports targeting on/off state, off variation, prerequisites, individual targets across context kinds, segment clauses, custom rules, default variation, event tracking, approval-aware saves, and preview evaluation with multi-context JSON.

Example preview context:

```json
{
  "user": {"key": "user-123", "plan": "pro"},
  "device": {"key": "phone-1", "platform": "ios"},
  "organization": {"key": "org-9", "tier": "enterprise"}
}
```
