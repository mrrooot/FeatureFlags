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
