# Django Feature Flags Platform Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working vertical slice of the embedded Django feature flag platform: installable package, database models, bootstrap command, evaluator, remote API, event capture, experiment allocation, audit hooks, and a premium dashboard shell.

**Architecture:** The package is a normal Django app under `src/django_feature_flags`. Models are split by domain and re-exported from `models/__init__.py`; evaluation, targeting, API, dashboard, events, experiments, and audit code live in focused modules. Local Python calls and remote API calls both use the same evaluator.

**Tech Stack:** Python 3.11+, Django 4.2+, pytest, pytest-django, SQLite test database, Django templates, plain CSS, Django ORM-compatible JSON fields.

---

## Runtime Note For This Worktree

Use the local virtual environment created at `.venv/`. In this Windows workspace, replace plan commands as follows:

- `pytest ...` becomes `.venv\Scripts\python.exe -m pytest ...`
- `python -m django ...` becomes `.venv\Scripts\python.exe -m django ...`

## Scope Split

The approved spec describes a full platform with several subsystems. This plan implements a complete foundation that can be installed, migrated, bootstrapped, evaluated, called through an API, and opened in a staff-only dashboard.

Separate implementation plans are required after this foundation for:

- dashboard form workflows and full Premium SaaS visual polish
- advanced experiment analytics, statistics, guardrail charts, and funnel reports
- approval review UI and production change workflows
- external non-Django SDK clients
- optional high-volume database acceleration

## File Structure

Create this structure:

```text
pyproject.toml
README.md
src/django_feature_flags/
  __init__.py
  apps.py
  flags.py
  settings.py
  urls.py
  models/
    __init__.py
    audit.py
    core.py
    events.py
    experiments.py
  targeting/
    __init__.py
    operators.py
    rollout.py
  evaluation/
    __init__.py
    evaluator.py
  api/
    __init__.py
    auth.py
    urls.py
    views.py
  dashboard/
    __init__.py
    urls.py
    views.py
  events/
    __init__.py
    service.py
  experiments/
    __init__.py
    service.py
  audit/
    __init__.py
    service.py
  management/
    __init__.py
    commands/
      __init__.py
      featureflags.py
  migrations/
    __init__.py
  templates/django_feature_flags/
    base.html
    dashboard.html
    flag_list.html
  static/django_feature_flags/
    dashboard.css
tests/
  __init__.py
  conftest.py
  settings.py
  urls.py
  test_api.py
  test_audit.py
  test_bootstrap_command.py
  test_dashboard.py
  test_evaluator.py
  test_events.py
  test_experiments.py
  test_flags_api.py
  test_management_commands.py
  test_models.py
  test_package_import.py
  test_targeting.py
```

Each domain module has one responsibility:

- `models/core.py`: projects, environments, flags, variations, states, segments, SDK keys
- `models/events.py`: runtime event storage
- `models/experiments.py`: metrics, experiments, allocations, snapshots
- `models/audit.py`: audit logs and approval requests
- `targeting/`: pure targeting operators and deterministic rollout hashing
- `evaluation/evaluator.py`: shared flag evaluation engine
- `flags.py`: local public Python API
- `api/`: remote SDK HTTP API
- `dashboard/`: staff-only web UI
- `events/service.py`: event recording
- `experiments/service.py`: experiment assignment
- `audit/service.py`: change logging
- `management/commands/featureflags.py`: bootstrap, import/export, key rotation, cleanup, snapshots

---

### Task 1: Package And Test Harness

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/django_feature_flags/__init__.py`
- Create: `src/django_feature_flags/apps.py`
- Create: `src/django_feature_flags/settings.py`
- Create: `src/django_feature_flags/urls.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/settings.py`
- Create: `tests/urls.py`
- Create: `tests/test_package_import.py`

- [ ] **Step 1: Write the failing package import test**

Create `tests/test_package_import.py`:

```python
import django_feature_flags


def test_package_exposes_version():
    assert django_feature_flags.__version__ == "0.1.0"
```

- [ ] **Step 2: Run the import test and verify it fails**

Run:

```bash
pytest tests/test_package_import.py -q
```

Expected: `ModuleNotFoundError: No module named 'django_feature_flags'`.

- [ ] **Step 3: Create package metadata and minimal Django app**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "django-featureflags"
version = "0.1.0"
description = "Embedded Django feature flag platform with dashboard, evaluation API, events, and experiments."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "Django>=4.2,<6.0",
]

[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-django>=4.8",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
django_feature_flags = [
  "templates/django_feature_flags/*.html",
  "static/django_feature_flags/*.css",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
pythonpath = ["src", "."]
testpaths = ["tests"]
```

Create `README.md`:

```markdown
# django-featureflags

Embedded Django feature flag platform with local evaluation, remote SDK API, dashboard, events, and experiments.
```

Create `src/django_feature_flags/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/django_feature_flags/apps.py`:

```python
from django.apps import AppConfig


class DjangoFeatureFlagsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_feature_flags"
    verbose_name = "Django Feature Flags"
```

Create `src/django_feature_flags/settings.py`:

```python
DEFAULT_ENVIRONMENTS = ("development", "staging", "production")
SDK_KEY_PREFIX = "dff"
```

Create `src/django_feature_flags/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("", include("django_feature_flags.dashboard.urls")),
    path("api/", include("django_feature_flags.api.urls")),
]
```

Create `tests/settings.py`:

```python
SECRET_KEY = "tests"
DEBUG = True
ROOT_URLCONF = "tests.urls"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_feature_flags",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

STATIC_URL = "static/"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]
```

Create `tests/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("flags/", include("django_feature_flags.urls")),
]
```

Create `tests/conftest.py`:

```python
import pytest


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="admin",
        password="password",
        is_staff=True,
    )
```

Create empty `tests/__init__.py`.

- [ ] **Step 4: Run the import test and verify it passes**

Run:

```bash
pytest tests/test_package_import.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit package scaffold**

Run:

```bash
git add pyproject.toml README.md src/django_feature_flags tests
git commit -m "feat: scaffold django feature flags package"
```

---

### Task 2: Core Database Models

**Files:**
- Create: `src/django_feature_flags/models/__init__.py`
- Create: `src/django_feature_flags/models/core.py`
- Create: `src/django_feature_flags/models/events.py`
- Create: `src/django_feature_flags/models/experiments.py`
- Create: `src/django_feature_flags/models/audit.py`
- Create: `src/django_feature_flags/migrations/__init__.py`
- Generate: `src/django_feature_flags/migrations/0001_initial.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/test_models.py`:

```python
import pytest

from django_feature_flags.models import (
    Environment,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Variation,
)


@pytest.mark.django_db
def test_flag_definition_is_global_and_state_is_per_environment():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    staging = Environment.objects.create(project=project, key="staging", name="Staging")
    production = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)

    staging_state = FlagState.objects.create(flag=flag, environment=staging, enabled=True, default_variation=on)
    production_state = FlagState.objects.create(flag=flag, environment=production, enabled=False, default_variation=off)

    assert flag.states.count() == 2
    assert staging_state.default_variation.value is True
    assert production_state.default_variation.value is False


@pytest.mark.django_db
def test_sdk_key_is_environment_specific_and_secret_is_hashed():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")

    sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")

    assert sdk_key.secret.startswith("dff_")
    assert sdk_key.secret_hash != sdk_key.secret
    assert SDKKey.objects.authenticate(sdk_key.secret) == sdk_key
```

- [ ] **Step 2: Run the model tests and verify they fail**

Run:

```bash
pytest tests/test_models.py -q
```

Expected: import failure for missing model classes.

- [ ] **Step 3: Implement domain models**

Create `src/django_feature_flags/models/core.py`:

```python
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from django_feature_flags import settings as package_settings


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Project(TimeStampedModel):
    key = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Environment(TimeStampedModel):
    project = models.ForeignKey(Project, related_name="environments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=160)
    requires_approval = models.BooleanField(default=False)
    require_change_reason = models.BooleanField(default=False)

    class Meta:
        ordering = ["project__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_environment_key_per_project"),
        ]

    def __str__(self):
        return f"{self.project.key}:{self.key}"


class FeatureFlag(TimeStampedModel):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"
    VALUE_TYPES = (
        (BOOLEAN, "Boolean"),
        (STRING, "String"),
        (NUMBER, "Number"),
        (JSON, "JSON"),
    )

    project = models.ForeignKey(Project, related_name="flags", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    value_type = models.CharField(max_length=20, choices=VALUE_TYPES)
    archived = models.BooleanField(default=False)
    rules = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["project__name", "key"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_flag_key_per_project"),
        ]

    def __str__(self):
        return self.key


class Variation(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="variations", on_delete=models.CASCADE)
    key = models.SlugField(max_length=80)
    name = models.CharField(max_length=120, blank=True)
    value = models.JSONField()
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["flag__key", "key"]
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_variation_key_per_flag"),
        ]

    def __str__(self):
        return f"{self.flag.key}:{self.key}"


class FlagState(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="states", on_delete=models.CASCADE)
    environment = models.ForeignKey(Environment, related_name="flag_states", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=False)
    default_variation = models.ForeignKey(Variation, related_name="+", null=True, blank=True, on_delete=models.PROTECT)
    rollout = models.JSONField(default=dict, blank=True)
    emergency_override = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["environment__project__name", "environment__name", "flag__key"]
        constraints = [
            models.UniqueConstraint(fields=["flag", "environment"], name="dff_unique_flag_state_per_environment"),
        ]

    def __str__(self):
        return f"{self.environment}:{self.flag.key}"


class Segment(TimeStampedModel):
    project = models.ForeignKey(Project, related_name="segments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["project__name", "key"]
        constraints = [
            models.UniqueConstraint(fields=["project", "key"], name="dff_unique_segment_key_per_project"),
        ]


class SegmentRule(TimeStampedModel):
    segment = models.ForeignKey(Segment, related_name="rules", on_delete=models.CASCADE)
    conditions = models.JSONField(default=list)
    exclude = models.BooleanField(default=False)


class TargetingRule(TimeStampedModel):
    flag = models.ForeignKey(FeatureFlag, related_name="targeting_rules", on_delete=models.CASCADE)
    priority = models.PositiveIntegerField(default=0)
    conditions = models.JSONField(default=list)
    variation = models.ForeignKey(Variation, related_name="+", on_delete=models.PROTECT)

    class Meta:
        ordering = ["flag__key", "priority", "id"]


class SDKKeyQuerySet(models.QuerySet):
    def authenticate(self, raw_secret):
        digest = SDKKey.hash_secret(raw_secret)
        return self.filter(secret_hash=digest, active=True).first()


class SDKKey(TimeStampedModel):
    environment = models.ForeignKey(Environment, related_name="sdk_keys", on_delete=models.CASCADE)
    name = models.CharField(max_length=160)
    secret_hash = models.CharField(max_length=128, unique=True)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    objects = SDKKeyQuerySet.as_manager()

    class Meta:
        ordering = ["environment__project__name", "environment__name", "name"]

    @staticmethod
    def hash_secret(raw_secret):
        return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_environment(cls, environment, name, created_by=None):
        raw_secret = f"{package_settings.SDK_KEY_PREFIX}_{secrets.token_urlsafe(32)}"
        instance = cls.objects.create(
            environment=environment,
            name=name,
            secret_hash=cls.hash_secret(raw_secret),
            created_by=created_by,
        )
        instance.secret = raw_secret
        return instance

    def __str__(self):
        return f"{self.environment}:{self.name}"
```

Create `src/django_feature_flags/models/events.py`:

```python
from django.db import models
from django.utils import timezone

from django_feature_flags.models.core import Environment, FeatureFlag, Variation


class Event(models.Model):
    EVALUATION = "evaluation"
    IMPRESSION = "impression"
    CONVERSION = "conversion"
    CUSTOM = "custom"
    EVENT_TYPES = (
        (EVALUATION, "Evaluation"),
        (IMPRESSION, "Impression"),
        (CONVERSION, "Conversion"),
        (CUSTOM, "Custom"),
    )

    environment = models.ForeignKey(Environment, related_name="events", on_delete=models.CASCADE)
    flag = models.ForeignKey(FeatureFlag, null=True, blank=True, related_name="events", on_delete=models.SET_NULL)
    variation = models.ForeignKey(Variation, null=True, blank=True, related_name="events", on_delete=models.SET_NULL)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    context_key = models.CharField(max_length=180, blank=True)
    metric_key = models.CharField(max_length=120, blank=True)
    value = models.FloatField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
```

Create `src/django_feature_flags/models/experiments.py`:

```python
from django.db import models

from django_feature_flags.models.core import FeatureFlag, Variation
from django_feature_flags.models.events import Event


class Metric(models.Model):
    CONVERSION = "conversion"
    FUNNEL = "funnel"
    GUARDRAIL = "guardrail"
    METRIC_TYPES = (
        (CONVERSION, "Conversion"),
        (FUNNEL, "Funnel"),
        (GUARDRAIL, "Guardrail"),
    )

    flag = models.ForeignKey(FeatureFlag, related_name="metrics", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    metric_type = models.CharField(max_length=20, choices=METRIC_TYPES)
    event_name = models.CharField(max_length=120)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_metric_key_per_flag"),
        ]


class Experiment(models.Model):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    STATUSES = (
        (DRAFT, "Draft"),
        (RUNNING, "Running"),
        (PAUSED, "Paused"),
        (STOPPED, "Stopped"),
    )

    flag = models.ForeignKey(FeatureFlag, related_name="experiments", on_delete=models.CASCADE)
    key = models.SlugField(max_length=120)
    name = models.CharField(max_length=180)
    status = models.CharField(max_length=20, choices=STATUSES, default=DRAFT)
    primary_metric = models.ForeignKey(Metric, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    guardrail_metrics = models.ManyToManyField(Metric, related_name="guardrail_experiments", blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["flag", "key"], name="dff_unique_experiment_key_per_flag"),
        ]


class ExperimentAllocation(models.Model):
    experiment = models.ForeignKey(Experiment, related_name="allocations", on_delete=models.CASCADE)
    variation = models.ForeignKey(Variation, related_name="experiment_allocations", on_delete=models.CASCADE)
    weight = models.PositiveIntegerField(default=0)
    holdout = models.BooleanField(default=False)


class ExperimentResultSnapshot(models.Model):
    experiment = models.ForeignKey(Experiment, related_name="result_snapshots", on_delete=models.CASCADE)
    event_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_for_experiment(cls, experiment):
        event_count = Event.objects.filter(flag=experiment.flag).count()
        conversion_count = Event.objects.filter(flag=experiment.flag, event_type=Event.CONVERSION).count()
        return cls.objects.create(
            experiment=experiment,
            event_count=event_count,
            conversion_count=conversion_count,
            summary={
                "event_count": event_count,
                "conversion_count": conversion_count,
            },
        )
```

Create `src/django_feature_flags/models/audit.py`:

```python
from django.conf import settings
from django.db import models
from django.utils import timezone

from django_feature_flags.models.core import Environment, FeatureFlag


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    environment = models.ForeignKey(Environment, null=True, blank=True, related_name="audit_logs", on_delete=models.SET_NULL)
    flag = models.ForeignKey(FeatureFlag, null=True, blank=True, related_name="audit_logs", on_delete=models.SET_NULL)
    action = models.CharField(max_length=120)
    reason = models.TextField(blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]


class ApprovalRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUSES = (
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
    )

    environment = models.ForeignKey(Environment, related_name="approval_requests", on_delete=models.CASCADE)
    flag = models.ForeignKey(FeatureFlag, related_name="approval_requests", on_delete=models.CASCADE)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=STATUSES, default=PENDING)
    reason = models.TextField(blank=True)
    proposed_change = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
```

Create `src/django_feature_flags/models/__init__.py`:

```python
from django_feature_flags.models.audit import ApprovalRequest, AuditLog
from django_feature_flags.models.core import (
    Environment,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Segment,
    SegmentRule,
    TargetingRule,
    Variation,
)
from django_feature_flags.models.events import Event
from django_feature_flags.models.experiments import (
    Experiment,
    ExperimentAllocation,
    ExperimentResultSnapshot,
    Metric,
)

__all__ = [
    "ApprovalRequest",
    "AuditLog",
    "Environment",
    "Event",
    "Experiment",
    "ExperimentAllocation",
    "ExperimentResultSnapshot",
    "FeatureFlag",
    "FlagState",
    "Metric",
    "Project",
    "SDKKey",
    "Segment",
    "SegmentRule",
    "TargetingRule",
    "Variation",
]
```

Create empty `src/django_feature_flags/migrations/__init__.py`.

- [ ] **Step 4: Generate the initial migration**

Run:

```bash
python -m django makemigrations django_feature_flags --settings=tests.settings
```

Expected: migration `src/django_feature_flags/migrations/0001_initial.py` is created.

- [ ] **Step 5: Run the model tests and verify they pass**

Run:

```bash
pytest tests/test_models.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit core models**

Run:

```bash
git add src/django_feature_flags/models src/django_feature_flags/migrations tests/test_models.py
git commit -m "feat: add feature flag data model"
```

---

### Task 3: Bootstrap Management Command

**Files:**
- Create: `src/django_feature_flags/management/__init__.py`
- Create: `src/django_feature_flags/management/commands/__init__.py`
- Create: `src/django_feature_flags/management/commands/featureflags.py`
- Test: `tests/test_bootstrap_command.py`

- [ ] **Step 1: Write failing bootstrap command tests**

Create `tests/test_bootstrap_command.py`:

```python
import pytest
from django.core.management import call_command

from django_feature_flags.models import Environment, Project, SDKKey


@pytest.mark.django_db
def test_bootstrap_creates_project_environments_and_sdk_keys():
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")

    project = Project.objects.get(key="ecommerce")
    assert project.name == "Ecommerce"
    assert set(project.environments.values_list("key", flat=True)) == {"development", "staging", "production"}
    assert SDKKey.objects.filter(environment__project=project).count() == 3


@pytest.mark.django_db
def test_bootstrap_is_idempotent():
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")
    call_command("featureflags", "bootstrap", "--project", "ecommerce", "--name", "Ecommerce")

    assert Project.objects.count() == 1
    assert Environment.objects.count() == 3
```

- [ ] **Step 2: Run bootstrap tests and verify they fail**

Run:

```bash
pytest tests/test_bootstrap_command.py -q
```

Expected: `Unknown command: 'featureflags'`.

- [ ] **Step 3: Implement bootstrap command**

Create empty `src/django_feature_flags/management/__init__.py` and `src/django_feature_flags/management/commands/__init__.py`.

Create `src/django_feature_flags/management/commands/featureflags.py`:

```python
from django.core.management.base import BaseCommand, CommandError

from django_feature_flags import settings as package_settings
from django_feature_flags.models import Environment, Project, SDKKey


class Command(BaseCommand):
    help = "Manage django-featureflags projects, environments, SDK keys, and maintenance tasks."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")

        bootstrap = subparsers.add_parser("bootstrap")
        bootstrap.add_argument("--project", default="default")
        bootstrap.add_argument("--name", default="Default")

    def handle(self, *args, **options):
        action = options.get("action")
        if action == "bootstrap":
            return self.handle_bootstrap(options)
        raise CommandError("Action is required. Use: bootstrap")

    def handle_bootstrap(self, options):
        project, _ = Project.objects.get_or_create(
            key=options["project"],
            defaults={"name": options["name"]},
        )
        created_keys = []
        for environment_key in package_settings.DEFAULT_ENVIRONMENTS:
            environment, _ = Environment.objects.get_or_create(
                project=project,
                key=environment_key,
                defaults={"name": environment_key.title()},
            )
            if not environment.sdk_keys.filter(name="Server SDK").exists():
                sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")
                created_keys.append((environment.key, sdk_key.secret))

        self.stdout.write(self.style.SUCCESS(f"Bootstrapped project {project.key}"))
        for environment_key, raw_secret in created_keys:
            self.stdout.write(f"{environment_key}: {raw_secret}")
```

- [ ] **Step 4: Run bootstrap tests and verify they pass**

Run:

```bash
pytest tests/test_bootstrap_command.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit bootstrap command**

Run:

```bash
git add src/django_feature_flags/management tests/test_bootstrap_command.py
git commit -m "feat: add featureflags bootstrap command"
```

---

### Task 4: Targeting Operators And Rollout Hashing

**Files:**
- Create: `src/django_feature_flags/targeting/__init__.py`
- Create: `src/django_feature_flags/targeting/operators.py`
- Create: `src/django_feature_flags/targeting/rollout.py`
- Test: `tests/test_targeting.py`

- [ ] **Step 1: Write failing targeting tests**

Create `tests/test_targeting.py`:

```python
from django_feature_flags.targeting.operators import conditions_match
from django_feature_flags.targeting.rollout import bucket_context


def test_conditions_match_context_attributes():
    context = {"key": "user-123", "plan": "pro", "age": 31, "email": "a@example.com"}
    conditions = [
        {"attribute": "plan", "operator": "equals", "value": "pro"},
        {"attribute": "age", "operator": "greater_than", "value": 30},
        {"attribute": "email", "operator": "contains", "value": "@example.com"},
    ]

    assert conditions_match(context, conditions) is True


def test_conditions_fail_when_one_condition_fails():
    context = {"key": "user-123", "plan": "free"}
    conditions = [{"attribute": "plan", "operator": "equals", "value": "pro"}]

    assert conditions_match(context, conditions) is False


def test_rollout_bucket_is_stable_between_calls():
    first = bucket_context("new_checkout", "user-123")
    second = bucket_context("new_checkout", "user-123")

    assert first == second
    assert 0 <= first < 100000
```

- [ ] **Step 2: Run targeting tests and verify they fail**

Run:

```bash
pytest tests/test_targeting.py -q
```

Expected: import failure for `django_feature_flags.targeting`.

- [ ] **Step 3: Implement targeting helpers**

Create empty `src/django_feature_flags/targeting/__init__.py`.

Create `src/django_feature_flags/targeting/operators.py`:

```python
import re
from datetime import date, datetime


def get_attribute(context, attribute):
    current = context
    for part in attribute.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def compare(actual, operator, expected):
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "contains":
        return actual is not None and str(expected) in str(actual)
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "matches":
        return actual is not None and re.search(str(expected), str(actual)) is not None
    if operator == "greater_than":
        return actual > expected
    if operator == "greater_than_or_equal":
        return actual >= expected
    if operator == "less_than":
        return actual < expected
    if operator == "less_than_or_equal":
        return actual <= expected
    if operator == "before":
        return parse_datetime(actual) < parse_datetime(expected)
    if operator == "after":
        return parse_datetime(actual) > parse_datetime(expected)
    return False


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value))


def conditions_match(context, conditions):
    for condition in conditions:
        actual = get_attribute(context, condition["attribute"])
        if not compare(actual, condition["operator"], condition.get("value")):
            return False
    return True
```

Create `src/django_feature_flags/targeting/rollout.py`:

```python
import hashlib


def bucket_context(flag_key, context_key, salt=""):
    payload = f"{flag_key}:{context_key}:{salt}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:12], 16) % 100000


def is_in_rollout(flag_key, context_key, percentage, salt=""):
    threshold = int(float(percentage) * 1000)
    return bucket_context(flag_key, context_key, salt=salt) < threshold
```

- [ ] **Step 4: Run targeting tests and verify they pass**

Run:

```bash
pytest tests/test_targeting.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit targeting helpers**

Run:

```bash
git add src/django_feature_flags/targeting tests/test_targeting.py
git commit -m "feat: add targeting operators and rollout hashing"
```

---

### Task 5: Shared Evaluation Engine

**Files:**
- Create: `src/django_feature_flags/evaluation/__init__.py`
- Create: `src/django_feature_flags/evaluation/evaluator.py`
- Test: `tests/test_evaluator.py`

- [ ] **Step 1: Write failing evaluator tests**

Create `tests/test_evaluator.py`:

```python
import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, TargetingRule, Variation


@pytest.fixture
def flag_setup():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    return project, environment, flag, off, on


@pytest.mark.django_db
def test_missing_flag_returns_default(flag_setup):
    project, environment, _, _, _ = flag_setup

    result = evaluate("missing", {"key": "user-1"}, default=True, project_key=project.key, environment_key=environment.key)

    assert result.value is True
    assert result.reason == "flag_not_found"


@pytest.mark.django_db
def test_disabled_flag_returns_environment_default(flag_setup):
    project, environment, _, _, _ = flag_setup

    result = evaluate("new_checkout", {"key": "user-1"}, default=True, project_key=project.key, environment_key=environment.key)

    assert result.value is False
    assert result.reason == "disabled"


@pytest.mark.django_db
def test_targeting_rule_returns_matched_variation(flag_setup):
    project, environment, flag, _, on = flag_setup
    state = flag.states.get(environment=environment)
    state.enabled = True
    state.save(update_fields=["enabled"])
    TargetingRule.objects.create(
        flag=flag,
        priority=1,
        variation=on,
        conditions=[{"attribute": "plan", "operator": "equals", "value": "pro"}],
    )

    result = evaluate("new_checkout", {"key": "user-1", "plan": "pro"}, default=False, project_key=project.key, environment_key=environment.key)

    assert result.value is True
    assert result.variation_key == "on"
    assert result.reason == "target_match"
```

- [ ] **Step 2: Run evaluator tests and verify they fail**

Run:

```bash
pytest tests/test_evaluator.py -q
```

Expected: import failure for `django_feature_flags.evaluation`.

- [ ] **Step 3: Implement evaluator**

Create empty `src/django_feature_flags/evaluation/__init__.py`.

Create `src/django_feature_flags/evaluation/evaluator.py`:

```python
from dataclasses import dataclass

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project
from django_feature_flags.targeting.operators import conditions_match
from django_feature_flags.targeting.rollout import is_in_rollout


@dataclass(frozen=True)
class EvaluationResult:
    value: object
    variation_key: str
    reason: str
    flag_key: str
    environment_key: str


def context_key(context):
    return str(context.get("key") or context.get("user", {}).get("key") or "anonymous")


def default_result(flag_key, environment_key, default, reason):
    return EvaluationResult(
        value=default,
        variation_key="",
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
    )


def variation_result(flag_key, environment_key, variation, reason):
    return EvaluationResult(
        value=variation.value,
        variation_key=variation.key,
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
    )


def evaluate(flag_key, context, default=None, project_key="default", environment_key="production", track=False):
    project = Project.objects.filter(key=project_key).first()
    if project is None:
        return default_result(flag_key, environment_key, default, "project_not_found")

    environment = Environment.objects.filter(project=project, key=environment_key).first()
    if environment is None:
        return default_result(flag_key, environment_key, default, "environment_not_found")

    flag = FeatureFlag.objects.filter(project=project, key=flag_key, archived=False).first()
    if flag is None:
        return default_result(flag_key, environment.key, default, "flag_not_found")

    state = FlagState.objects.filter(flag=flag, environment=environment).select_related("default_variation").first()
    if state is None or state.default_variation is None:
        return default_result(flag_key, environment.key, default, "state_not_found")

    if state.emergency_override.get("variation_key"):
        variation = flag.variations.filter(key=state.emergency_override["variation_key"]).first()
        if variation is not None:
            return variation_result(flag.key, environment.key, variation, "emergency_override")

    if not state.enabled:
        return variation_result(flag.key, environment.key, state.default_variation, "disabled")

    for rule in flag.targeting_rules.select_related("variation").order_by("priority", "id"):
        if conditions_match(context, rule.conditions):
            return variation_result(flag.key, environment.key, rule.variation, "target_match")

    rollout = state.rollout or {}
    if rollout.get("percentage") and rollout.get("variation_key"):
        if is_in_rollout(flag.key, context_key(context), rollout["percentage"], salt=environment.key):
            variation = flag.variations.filter(key=rollout["variation_key"]).first()
            if variation is not None:
                return variation_result(flag.key, environment.key, variation, "rollout")

    return variation_result(flag.key, environment.key, state.default_variation, "fallthrough")
```

- [ ] **Step 4: Run evaluator tests and verify they pass**

Run:

```bash
pytest tests/test_evaluator.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit evaluator**

Run:

```bash
git add src/django_feature_flags/evaluation tests/test_evaluator.py
git commit -m "feat: add shared evaluation engine"
```

---

### Task 6: Local Public Python API

**Files:**
- Create: `src/django_feature_flags/flags.py`
- Test: `tests/test_flags_api.py`

- [ ] **Step 1: Write failing local API tests**

Create `tests/test_flags_api.py`:

```python
import pytest

from django_feature_flags import flags
from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_bool_variation_returns_boolean_value():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    assert flags.bool_variation("new_checkout", {"key": "user-1"}, default=False, project="ecommerce", environment="production") is True


@pytest.mark.django_db
def test_string_variation_returns_default_when_flag_missing():
    assert flags.string_variation("missing", {"key": "user-1"}, default="control", project="ecommerce", environment="production") == "control"
```

- [ ] **Step 2: Run local API tests and verify they fail**

Run:

```bash
pytest tests/test_flags_api.py -q
```

Expected: import failure for `flags`.

- [ ] **Step 3: Implement local API wrappers**

Create `src/django_feature_flags/flags.py`:

```python
from django_feature_flags.evaluation.evaluator import evaluate


def variation(flag_key, context, default=None, project="default", environment="production", track=False):
    return evaluate(
        flag_key,
        context,
        default=default,
        project_key=project,
        environment_key=environment,
        track=track,
    ).value


def bool_variation(flag_key, context, default=False, project="default", environment="production", track=False):
    return bool(variation(flag_key, context, default=default, project=project, environment=environment, track=track))


def string_variation(flag_key, context, default="", project="default", environment="production", track=False):
    value = variation(flag_key, context, default=default, project=project, environment=environment, track=track)
    return str(value)


def number_variation(flag_key, context, default=0, project="default", environment="production", track=False):
    value = variation(flag_key, context, default=default, project=project, environment=environment, track=track)
    return value


def json_variation(flag_key, context, default=None, project="default", environment="production", track=False):
    fallback = {} if default is None else default
    return variation(flag_key, context, default=fallback, project=project, environment=environment, track=track)
```

- [ ] **Step 4: Run local API tests and verify they pass**

Run:

```bash
pytest tests/test_flags_api.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit local API**

Run:

```bash
git add src/django_feature_flags/flags.py tests/test_flags_api.py
git commit -m "feat: add local flag variation api"
```

---

### Task 7: Remote SDK Evaluation API

**Files:**
- Create: `src/django_feature_flags/api/__init__.py`
- Create: `src/django_feature_flags/api/auth.py`
- Create: `src/django_feature_flags/api/urls.py`
- Create: `src/django_feature_flags/api/views.py`
- Modify: `src/django_feature_flags/urls.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

Create `tests/test_api.py`:

```python
import json

import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, SDKKey, Variation


@pytest.mark.django_db
def test_evaluate_endpoint_requires_valid_sdk_key(client):
    response = client.post("/flags/api/evaluate/", data={}, content_type="application/json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_evaluate_endpoint_returns_variation_for_sdk_environment(client):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    key = SDKKey.create_for_environment(environment, name="Server SDK")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    response = client.post(
        "/flags/api/evaluate/",
        data=json.dumps({"flag_key": "new_checkout", "context": {"key": "user-1"}, "default": False}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {key.secret}",
    )

    assert response.status_code == 200
    assert response.json()["value"] is True
    assert response.json()["variation_key"] == "on"
```

- [ ] **Step 2: Run API tests and verify they fail**

Run:

```bash
pytest tests/test_api.py -q
```

Expected: URL import failure for missing API modules.

- [ ] **Step 3: Implement SDK API**

Create empty `src/django_feature_flags/api/__init__.py`.

Create `src/django_feature_flags/api/auth.py`:

```python
from django_feature_flags.models import SDKKey


def authenticate_request(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Bearer "):
        return None
    raw_secret = header.removeprefix("Bearer ").strip()
    return SDKKey.objects.authenticate(raw_secret)
```

Create `src/django_feature_flags/api/views.py`:

```python
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_feature_flags.api.auth import authenticate_request
from django_feature_flags.evaluation.evaluator import evaluate


@csrf_exempt
@require_POST
def evaluate_view(request):
    sdk_key = authenticate_request(request)
    if sdk_key is None:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    result = evaluate(
        payload.get("flag_key", ""),
        payload.get("context", {}),
        default=payload.get("default"),
        project_key=sdk_key.environment.project.key,
        environment_key=sdk_key.environment.key,
        track=payload.get("track", False),
    )
    return JsonResponse(
        {
            "value": result.value,
            "variation_key": result.variation_key,
            "reason": result.reason,
            "flag_key": result.flag_key,
            "environment_key": result.environment_key,
        }
    )
```

Create `src/django_feature_flags/api/urls.py`:

```python
from django.urls import path

from django_feature_flags.api.views import evaluate_view

app_name = "django_feature_flags_api"

urlpatterns = [
    path("evaluate/", evaluate_view, name="evaluate"),
]
```

- [ ] **Step 4: Run API tests and verify they pass**

Run:

```bash
pytest tests/test_api.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit SDK API**

Run:

```bash
git add src/django_feature_flags/api src/django_feature_flags/urls.py tests/test_api.py
git commit -m "feat: add remote sdk evaluation api"
```

---

### Task 8: Event Capture Service

**Files:**
- Create: `src/django_feature_flags/events/__init__.py`
- Create: `src/django_feature_flags/events/service.py`
- Modify: `src/django_feature_flags/evaluation/evaluator.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write failing event tests**

Create `tests/test_events.py`:

```python
import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import Environment, Event, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_tracked_evaluation_records_event():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    on = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=on)

    evaluate("new_checkout", {"key": "user-1"}, default=False, project_key="ecommerce", environment_key="production", track=True)

    event = Event.objects.get()
    assert event.event_type == Event.EVALUATION
    assert event.context_key == "user-1"
    assert event.variation == on
```

- [ ] **Step 2: Run event tests and verify they fail**

Run:

```bash
pytest tests/test_events.py -q
```

Expected: assertion failure because no event is recorded.

- [ ] **Step 3: Implement event recording and call it from evaluator**

Create empty `src/django_feature_flags/events/__init__.py`.

Create `src/django_feature_flags/events/service.py`:

```python
from django_feature_flags.models import Event


def record_evaluation(environment, flag, variation, context, payload=None):
    return Event.objects.create(
        environment=environment,
        flag=flag,
        variation=variation,
        event_type=Event.EVALUATION,
        context_key=str(context.get("key", "")),
        payload=payload or {},
    )
```

Modify `src/django_feature_flags/evaluation/evaluator.py` so `variation_result` accepts tracking details:

```python
def variation_result(flag_key, environment_key, variation, reason):
    return EvaluationResult(
        value=variation.value,
        variation_key=variation.key,
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
    )
```

Then add this helper below `variation_result`:

```python
def tracked_result(environment, flag, variation, context, reason, track):
    if track:
        from django_feature_flags.events.service import record_evaluation

        record_evaluation(environment, flag, variation, context, payload={"reason": reason})
    return variation_result(flag.key, environment.key, variation, reason)
```

Replace every `return variation_result(flag.key, environment.key, ...` call inside `evaluate` with `return tracked_result(environment, flag, ..., context, "<reason>", track)`. For example:

```python
if not state.enabled:
    return tracked_result(environment, flag, state.default_variation, context, "disabled", track)
```

- [ ] **Step 4: Run event tests and evaluator tests**

Run:

```bash
pytest tests/test_events.py tests/test_evaluator.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit event capture**

Run:

```bash
git add src/django_feature_flags/events src/django_feature_flags/evaluation/evaluator.py tests/test_events.py
git commit -m "feat: record evaluation events"
```

---

### Task 9: Experiment Allocation Service

**Files:**
- Create: `src/django_feature_flags/experiments/__init__.py`
- Create: `src/django_feature_flags/experiments/service.py`
- Modify: `src/django_feature_flags/evaluation/evaluator.py`
- Test: `tests/test_experiments.py`

- [ ] **Step 1: Write failing experiment allocation tests**

Create `tests/test_experiments.py`:

```python
import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.experiments.service import choose_experiment_variation
from django_feature_flags.models import (
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    FlagState,
    Project,
    Variation,
)


@pytest.mark.django_db
def test_choose_experiment_variation_is_stable_for_context():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    control = Variation.objects.create(flag=flag, key="control", value=False)
    treatment = Variation.objects.create(flag=flag, key="treatment", value=True)
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)
    ExperimentAllocation.objects.create(experiment=experiment, variation=control, weight=50000)
    ExperimentAllocation.objects.create(experiment=experiment, variation=treatment, weight=50000)

    first = choose_experiment_variation(experiment, {"key": "user-1"})
    second = choose_experiment_variation(experiment, {"key": "user-1"})

    assert first == second
    assert first.key in {"control", "treatment"}


@pytest.mark.django_db
def test_evaluator_uses_running_experiment_before_fallthrough():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=off)
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)
    ExperimentAllocation.objects.create(experiment=experiment, variation=on, weight=100000)

    result = evaluate("new_checkout", {"key": "user-1"}, default=False, project_key="ecommerce", environment_key="production")

    assert result.value is True
    assert result.reason == "experiment"
```

- [ ] **Step 2: Run experiment tests and verify they fail**

Run:

```bash
pytest tests/test_experiments.py -q
```

Expected: import failure for `django_feature_flags.experiments.service`.

- [ ] **Step 3: Implement experiment assignment**

Create empty `src/django_feature_flags/experiments/__init__.py`.

Create `src/django_feature_flags/experiments/service.py`:

```python
from django_feature_flags.models import Experiment
from django_feature_flags.targeting.rollout import bucket_context


def choose_experiment_variation(experiment, context):
    context_key = str(context.get("key", "anonymous"))
    bucket = bucket_context(experiment.flag.key, context_key, salt=experiment.key)
    cursor = 0
    for allocation in experiment.allocations.select_related("variation").order_by("id"):
        cursor += allocation.weight
        if bucket < cursor:
            return allocation.variation
    return None


def active_experiment_for_flag(flag):
    return flag.experiments.filter(status=Experiment.RUNNING).order_by("id").first()
```

Modify `src/django_feature_flags/evaluation/evaluator.py` after targeting rules and before rollout:

```python
    from django_feature_flags.experiments.service import active_experiment_for_flag, choose_experiment_variation

    experiment = active_experiment_for_flag(flag)
    if experiment is not None:
        variation = choose_experiment_variation(experiment, context)
        if variation is not None:
            return tracked_result(environment, flag, variation, context, "experiment", track)
```

- [ ] **Step 4: Run experiment and evaluator tests**

Run:

```bash
pytest tests/test_experiments.py tests/test_evaluator.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit experiment allocation**

Run:

```bash
git add src/django_feature_flags/experiments src/django_feature_flags/evaluation/evaluator.py tests/test_experiments.py
git commit -m "feat: add experiment allocation"
```

---

### Task 10: Staff-Only Dashboard Shell

**Files:**
- Create: `src/django_feature_flags/dashboard/__init__.py`
- Create: `src/django_feature_flags/dashboard/urls.py`
- Create: `src/django_feature_flags/dashboard/views.py`
- Create: `src/django_feature_flags/templates/django_feature_flags/base.html`
- Create: `src/django_feature_flags/templates/django_feature_flags/dashboard.html`
- Create: `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- Create: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Test: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing dashboard tests**

Create `tests/test_dashboard.py`:

```python
import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.mark.django_db
def test_dashboard_requires_staff(client):
    response = client.get("/flags/")

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.django_db
def test_staff_can_view_flag_list(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    client.force_login(staff_user)

    response = client.get("/flags/flags/")

    assert response.status_code == 200
    assert b"new_checkout" in response.content
    assert b"Premium SaaS" in response.content
```

- [ ] **Step 2: Run dashboard tests and verify they fail**

Run:

```bash
pytest tests/test_dashboard.py -q
```

Expected: URL import failure for missing dashboard modules.

- [ ] **Step 3: Implement dashboard views and templates**

Create empty `src/django_feature_flags/dashboard/__init__.py`.

Create `src/django_feature_flags/dashboard/views.py`:

```python
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from django_feature_flags.models import FeatureFlag, Project


@staff_member_required
def dashboard_home(request):
    context = {
        "project_count": Project.objects.count(),
        "flag_count": FeatureFlag.objects.count(),
        "style_name": "Premium SaaS",
    }
    return render(request, "django_feature_flags/dashboard.html", context)


@staff_member_required
def flag_list(request):
    flags = FeatureFlag.objects.select_related("project").prefetch_related("states__environment").order_by("project__name", "key")
    return render(request, "django_feature_flags/flag_list.html", {"flags": flags, "style_name": "Premium SaaS"})
```

Create `src/django_feature_flags/dashboard/urls.py`:

```python
from django.urls import path

from django_feature_flags.dashboard import views

app_name = "django_feature_flags_dashboard"

urlpatterns = [
    path("", views.dashboard_home, name="home"),
    path("flags/", views.flag_list, name="flag_list"),
]
```

Create `src/django_feature_flags/templates/django_feature_flags/base.html`:

```html
{% load static %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Django Feature Flags</title>
  <link rel="stylesheet" href="{% static 'django_feature_flags/dashboard.css' %}">
</head>
<body>
  <aside class="dff-sidebar">
    <div class="dff-brand">FeatureFlow</div>
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
  <main class="dff-main">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

Create `src/django_feature_flags/templates/django_feature_flags/dashboard.html`:

```html
{% extends "django_feature_flags/base.html" %}

{% block content %}
<header class="dff-header">
  <div>
    <p class="dff-kicker">{{ style_name }}</p>
    <h1>Control Center</h1>
  </div>
</header>
<section class="dff-grid">
  <article class="dff-panel">
    <span class="dff-label">Projects</span>
    <strong>{{ project_count }}</strong>
  </article>
  <article class="dff-panel">
    <span class="dff-label">Flags</span>
    <strong>{{ flag_count }}</strong>
  </article>
  <article class="dff-panel dff-panel-dark">
    <span class="dff-label">Experiment health</span>
    <strong>Ready</strong>
  </article>
</section>
{% endblock %}
```

Create `src/django_feature_flags/templates/django_feature_flags/flag_list.html`:

```html
{% extends "django_feature_flags/base.html" %}

{% block content %}
<header class="dff-header">
  <div>
    <p class="dff-kicker">{{ style_name }}</p>
    <h1>Flags</h1>
  </div>
</header>
<section class="dff-panel">
  <table class="dff-table">
    <thead>
      <tr>
        <th>Flag</th>
        <th>Project</th>
        <th>Type</th>
        <th>Archived</th>
      </tr>
    </thead>
    <tbody>
      {% for flag in flags %}
      <tr>
        <td><strong>{{ flag.key }}</strong><span>{{ flag.name }}</span></td>
        <td>{{ flag.project.key }}</td>
        <td>{{ flag.value_type }}</td>
        <td>{{ flag.archived|yesno:"Yes,No" }}</td>
      </tr>
      {% empty %}
      <tr><td colspan="4">No flags yet.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
```

Create `src/django_feature_flags/static/django_feature_flags/dashboard.css`:

```css
:root {
  color-scheme: light;
  --dff-bg: #f6f8fb;
  --dff-panel: #ffffff;
  --dff-text: #111827;
  --dff-muted: #64748b;
  --dff-line: #d7dee8;
  --dff-accent: #2563eb;
  --dff-success: #059669;
}

body {
  margin: 0;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  background: var(--dff-bg);
  color: var(--dff-text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.dff-sidebar {
  background: #ffffff;
  border-right: 1px solid var(--dff-line);
  padding: 24px;
}

.dff-brand {
  font-weight: 800;
  font-size: 18px;
  margin-bottom: 28px;
}

.dff-sidebar nav {
  display: grid;
  gap: 8px;
}

.dff-sidebar a {
  color: #334155;
  text-decoration: none;
  padding: 10px 12px;
  border-radius: 7px;
  font-weight: 650;
}

.dff-sidebar a:hover {
  background: #eef2f7;
}

.dff-main {
  padding: 32px;
}

.dff-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.dff-kicker,
.dff-label {
  color: var(--dff-muted);
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0;
  margin: 0 0 6px;
}

h1 {
  margin: 0;
  font-size: 30px;
}

.dff-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.dff-panel {
  background: var(--dff-panel);
  border: 1px solid var(--dff-line);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08);
}

.dff-panel strong {
  display: block;
  font-size: 28px;
}

.dff-panel-dark {
  background: #111827;
  color: #ffffff;
}

.dff-table {
  width: 100%;
  border-collapse: collapse;
}

.dff-table th,
.dff-table td {
  padding: 14px 12px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
}

.dff-table th {
  color: var(--dff-muted);
  font-size: 12px;
}

.dff-table td span {
  display: block;
  color: var(--dff-muted);
  font-size: 12px;
  margin-top: 4px;
}
```

- [ ] **Step 4: Run dashboard tests and verify they pass**

Run:

```bash
pytest tests/test_dashboard.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit dashboard shell**

Run:

```bash
git add src/django_feature_flags/dashboard src/django_feature_flags/templates src/django_feature_flags/static tests/test_dashboard.py
git commit -m "feat: add staff dashboard shell"
```

---

### Task 11: Audit Service And Approval Requests

**Files:**
- Create: `src/django_feature_flags/audit/__init__.py`
- Create: `src/django_feature_flags/audit/service.py`
- Test: `tests/test_audit.py`

- [ ] **Step 1: Write failing audit tests**

Create `tests/test_audit.py`:

```python
import pytest

from django_feature_flags.audit.service import create_audit_log, create_approval_request
from django_feature_flags.models import ApprovalRequest, AuditLog, Environment, FeatureFlag, Project


@pytest.mark.django_db
def test_create_audit_log_records_before_after(staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")

    log = create_audit_log(
        user=staff_user,
        environment=environment,
        flag=flag,
        action="flag.update",
        before={"enabled": False},
        after={"enabled": True},
        reason="Release checkout",
    )

    assert AuditLog.objects.get() == log
    assert log.before["enabled"] is False
    assert log.after["enabled"] is True


@pytest.mark.django_db
def test_create_approval_request_for_environment(staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")

    request = create_approval_request(
        requested_by=staff_user,
        environment=environment,
        flag=flag,
        proposed_change={"enabled": True},
        reason="Production launch",
    )

    assert request.status == ApprovalRequest.PENDING
    assert request.proposed_change["enabled"] is True
```

- [ ] **Step 2: Run audit tests and verify they fail**

Run:

```bash
pytest tests/test_audit.py -q
```

Expected: import failure for `django_feature_flags.audit.service`.

- [ ] **Step 3: Implement audit service**

Create empty `src/django_feature_flags/audit/__init__.py`.

Create `src/django_feature_flags/audit/service.py`:

```python
from django_feature_flags.models import ApprovalRequest, AuditLog


def create_audit_log(user, environment, flag, action, before, after, reason=""):
    return AuditLog.objects.create(
        user=user,
        environment=environment,
        flag=flag,
        action=action,
        before=before,
        after=after,
        reason=reason,
    )


def create_approval_request(requested_by, environment, flag, proposed_change, reason=""):
    return ApprovalRequest.objects.create(
        requested_by=requested_by,
        environment=environment,
        flag=flag,
        proposed_change=proposed_change,
        reason=reason,
    )
```

- [ ] **Step 4: Run audit tests and verify they pass**

Run:

```bash
pytest tests/test_audit.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit audit service**

Run:

```bash
git add src/django_feature_flags/audit tests/test_audit.py
git commit -m "feat: add audit and approval services"
```

---

### Task 12: Export, Import, Key Rotation, Cleanup, And Snapshots

**Files:**
- Modify: `src/django_feature_flags/management/commands/featureflags.py`
- Test: `tests/test_management_commands.py`

- [ ] **Step 1: Write failing management command tests**

Create `tests/test_management_commands.py`:

```python
import json
from io import StringIO

import pytest
from django.core.management import call_command

from django_feature_flags.models import (
    Environment,
    Event,
    Experiment,
    ExperimentResultSnapshot,
    FeatureFlag,
    FlagState,
    Project,
    SDKKey,
    Variation,
)


@pytest.mark.django_db
def test_export_omits_sdk_keys_and_events():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    SDKKey.create_for_environment(environment, name="Server SDK")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    variation = Variation.objects.create(flag=flag, key="on", value=True, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=True, default_variation=variation)
    Event.objects.create(environment=environment, flag=flag, variation=variation, event_type=Event.EVALUATION, context_key="user-1")
    output = StringIO()

    call_command("featureflags", "export", "--project", "ecommerce", stdout=output)

    payload = json.loads(output.getvalue())
    assert payload["project"]["key"] == "ecommerce"
    assert payload["flags"][0]["key"] == "new_checkout"
    assert "sdk_keys" not in payload
    assert "events" not in payload


@pytest.mark.django_db
def test_rotate_key_deactivates_old_key_and_creates_new_key():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    old_key = SDKKey.create_for_environment(environment, name="Server SDK")
    output = StringIO()

    call_command("featureflags", "rotate-key", "--project", "ecommerce", "--environment", "production", stdout=output)

    old_key.refresh_from_db()
    assert old_key.active is False
    assert SDKKey.objects.filter(environment=environment, active=True).count() == 1
    assert "dff_" in output.getvalue()


@pytest.mark.django_db
def test_snapshot_results_creates_experiment_snapshot():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    experiment = Experiment.objects.create(flag=flag, key="checkout_test", name="Checkout Test", status=Experiment.RUNNING)

    call_command("featureflags", "snapshot-results")

    assert ExperimentResultSnapshot.objects.filter(experiment=experiment).exists()
```

- [ ] **Step 2: Run management command tests and verify they fail**

Run:

```bash
pytest tests/test_management_commands.py -q
```

Expected: `CommandError` because `export`, `rotate-key`, and `snapshot-results` are not implemented.

- [ ] **Step 3: Extend command parser and handlers**

Modify `add_arguments` in `src/django_feature_flags/management/commands/featureflags.py`:

```python
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="action")

        bootstrap = subparsers.add_parser("bootstrap")
        bootstrap.add_argument("--project", default="default")
        bootstrap.add_argument("--name", default="Default")

        export = subparsers.add_parser("export")
        export.add_argument("--project", required=True)

        import_cmd = subparsers.add_parser("import")
        import_cmd.add_argument("path")

        rotate = subparsers.add_parser("rotate-key")
        rotate.add_argument("--project", required=True)
        rotate.add_argument("--environment", required=True)

        cleanup = subparsers.add_parser("cleanup-events")
        cleanup.add_argument("--days", type=int, default=90)

        subparsers.add_parser("snapshot-results")
```

Modify `handle`:

```python
    def handle(self, *args, **options):
        action = options.get("action")
        if action == "bootstrap":
            return self.handle_bootstrap(options)
        if action == "export":
            return self.handle_export(options)
        if action == "import":
            return self.handle_import(options)
        if action == "rotate-key":
            return self.handle_rotate_key(options)
        if action == "cleanup-events":
            return self.handle_cleanup_events(options)
        if action == "snapshot-results":
            return self.handle_snapshot_results(options)
        raise CommandError("Action is required.")
```

Add imports at the top:

```python
import json
from datetime import timedelta

from django.utils import timezone

from django_feature_flags.models import Event, Experiment, ExperimentResultSnapshot, FeatureFlag, FlagState, Variation
```

Add handlers to the command class:

```python
    def handle_export(self, options):
        project = Project.objects.get(key=options["project"])
        payload = {
            "project": {"key": project.key, "name": project.name, "description": project.description},
            "environments": list(project.environments.values("key", "name", "requires_approval", "require_change_reason")),
            "flags": [],
        }
        for flag in project.flags.prefetch_related("variations", "states__environment"):
            payload["flags"].append(
                {
                    "key": flag.key,
                    "name": flag.name,
                    "description": flag.description,
                    "value_type": flag.value_type,
                    "archived": flag.archived,
                    "rules": flag.rules,
                    "variations": list(flag.variations.values("key", "name", "value", "is_default")),
                    "states": [
                        {
                            "environment": state.environment.key,
                            "enabled": state.enabled,
                            "default_variation": state.default_variation.key if state.default_variation else "",
                            "rollout": state.rollout,
                            "emergency_override": state.emergency_override,
                        }
                        for state in flag.states.select_related("environment", "default_variation")
                    ],
                }
            )
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))

    def handle_import(self, options):
        with open(options["path"], "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        project_data = payload["project"]
        project, _ = Project.objects.update_or_create(
            key=project_data["key"],
            defaults={"name": project_data["name"], "description": project_data.get("description", "")},
        )
        environments = {}
        for item in payload["environments"]:
            environment, _ = Environment.objects.update_or_create(
                project=project,
                key=item["key"],
                defaults={
                    "name": item["name"],
                    "requires_approval": item.get("requires_approval", False),
                    "require_change_reason": item.get("require_change_reason", False),
                },
            )
            environments[environment.key] = environment
        for flag_data in payload["flags"]:
            flag, _ = FeatureFlag.objects.update_or_create(
                project=project,
                key=flag_data["key"],
                defaults={
                    "name": flag_data["name"],
                    "description": flag_data.get("description", ""),
                    "value_type": flag_data["value_type"],
                    "archived": flag_data.get("archived", False),
                    "rules": flag_data.get("rules", []),
                },
            )
            variations = {}
            for item in flag_data["variations"]:
                variation, _ = Variation.objects.update_or_create(
                    flag=flag,
                    key=item["key"],
                    defaults={"name": item.get("name", ""), "value": item["value"], "is_default": item.get("is_default", False)},
                )
                variations[variation.key] = variation
            for item in flag_data["states"]:
                FlagState.objects.update_or_create(
                    flag=flag,
                    environment=environments[item["environment"]],
                    defaults={
                        "enabled": item["enabled"],
                        "default_variation": variations.get(item.get("default_variation")),
                        "rollout": item.get("rollout", {}),
                        "emergency_override": item.get("emergency_override", {}),
                    },
                )
        self.stdout.write(self.style.SUCCESS("Imported feature flag configuration"))

    def handle_rotate_key(self, options):
        environment = Environment.objects.get(project__key=options["project"], key=options["environment"])
        environment.sdk_keys.filter(active=True).update(active=False)
        sdk_key = SDKKey.create_for_environment(environment, name="Server SDK")
        self.stdout.write(sdk_key.secret)

    def handle_cleanup_events(self, options):
        cutoff = timezone.now() - timedelta(days=options["days"])
        deleted, _ = Event.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(str(deleted))

    def handle_snapshot_results(self, options):
        count = 0
        for experiment in Experiment.objects.all():
            ExperimentResultSnapshot.create_for_experiment(experiment)
            count += 1
        self.stdout.write(str(count))
```

- [ ] **Step 4: Run management command tests and bootstrap tests**

Run:

```bash
pytest tests/test_management_commands.py tests/test_bootstrap_command.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit management commands**

Run:

```bash
git add src/django_feature_flags/management/commands/featureflags.py tests/test_management_commands.py
git commit -m "feat: add feature flag management commands"
```

---

### Task 13: Documentation And Full Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with installation and usage**

Replace `README.md` with:

````markdown
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
````

- [ ] **Step 2: Run full test suite**

Run:

```bash
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run Django system checks**

Run:

```bash
python -m django check --settings=tests.settings
```

Expected: `System check identified no issues`.

- [ ] **Step 4: Inspect git state**

Run:

```bash
git status --short
```

Expected: only `README.md` is modified.

- [ ] **Step 5: Commit documentation and verification pass**

Run:

```bash
git add README.md
git commit -m "docs: add package usage guide"
```

---

## Self-Review

Spec coverage in this foundation plan:

- Multiple projects and environments: Task 2 and Task 3
- Global flag definitions with per-environment state: Task 2 and Task 5
- Boolean/string/number/JSON variations: Task 2 and Task 6
- Targeting rules and percentage rollouts: Task 4 and Task 5
- Local Python evaluation API: Task 6
- Remote SDK evaluation API with SDK keys: Task 7
- Staff/admin dashboard shell: Task 10
- Evaluation event capture: Task 8
- Experiment allocation foundation: Task 9
- Audit logs and approval requests foundation: Task 11
- Management commands: Task 12
- Packaging and tests: Task 1 and Task 13

Known follow-up plans required for the full approved spec:

- full flag create/edit dashboard workflows
- segment create/edit UI and segment matching in the evaluator
- prerequisite flag evaluation
- advanced experiment result analysis with confidence, lift, guardrails, and funnels
- rich analytics charts and event aggregation pages
- approval review UI and production change enforcement
- visual regression checks for the Premium SaaS dashboard
- external SDK packages for non-Django services
