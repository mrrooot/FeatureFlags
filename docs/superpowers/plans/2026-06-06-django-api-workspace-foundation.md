# Django API Workspace Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the first working slice of the new `django-api-workspace` package: installable Django app, authenticated user dashboard, user-created workspaces, role permissions, protocol-aware API documentation models, dashboard-first CRUD, private-by-default public docs, and bootstrap automation.

**Architecture:** Build a new standalone Django package under `src/django_api_workspace` with small modules for accounts, workspace core, dashboard, docs, and models. This foundation intentionally creates protocol-aware models for REST, GraphQL, WebSocket, and gRPC from day one while leaving deep importers, protocol runners, and static export for follow-up implementation plans.

**Tech Stack:** Python 3.10+, Django 4.2-5.x, pytest, pytest-django, setuptools, SQLite-compatible Django ORM.

---

## Scope Check

The approved spec is platform-sized and contains several independent subsystems. This plan covers the first testable foundation slice:

- package scaffold
- Django app installation
- auth-backed account entry points
- workspace ownership and membership
- core collection/group/endpoint/documentation/example models
- protocol detail models for REST, GraphQL, WebSocket, and gRPC
- environments, variables, auth profiles, history, saved responses, assertions, jobs, and audit models
- dashboard routes/templates for login, registration, workspace list/detail, collection creation, and endpoint creation
- private-by-default public docs route
- bootstrap management command

Separate implementation plans should cover:

- importers and host discovery
- protocol runner adapters and visual tests
- public docs publishing, token access, and static export
- dashboard polish and advanced workflows

All paths below are relative to the new project root `DjangoApiWorkspace/`.

---

## File Structure

Create this project structure:

```text
DjangoApiWorkspace/
  .gitignore
  README.md
  pyproject.toml
  src/
    django_api_workspace/
      __init__.py
      apps.py
      settings.py
      urls.py
      accounts/
        __init__.py
        forms.py
        views.py
      core/
        __init__.py
        permissions.py
        services.py
      dashboard/
        __init__.py
        forms.py
        views.py
        urls.py
      docs/
        __init__.py
        views.py
        urls.py
      management/
        __init__.py
        commands/
          __init__.py
          apiworkspace.py
      migrations/
        __init__.py
      models/
        __init__.py
        apis.py
        audit.py
        jobs.py
        runtime.py
        workspaces.py
      templates/
        django_api_workspace/
          base.html
          accounts/
            login.html
            register.html
          dashboard/
            endpoint_form.html
            home.html
            workspace_detail.html
            workspace_form.html
          docs/
            workspace_public.html
  tests/
    __init__.py
    conftest.py
    settings.py
    urls.py
    test_dashboard.py
    test_management_commands.py
    test_models.py
    test_package_import.py
    test_permissions.py
    test_public_docs.py
```

Responsibilities:

- `accounts`: package-provided auth forms and views.
- `core`: permission checks and workspace service APIs reused by views and commands.
- `dashboard`: authenticated dashboard forms, views, and URL routing.
- `docs`: public documentation views.
- `models`: focused domain model modules imported by `models/__init__.py`.
- `management`: command mirrors for automation.
- `tests`: pytest-django coverage for each foundation behavior.

---

### Task 1: Package Scaffold And Test Settings

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `pyproject.toml`
- Create: `src/django_api_workspace/__init__.py`
- Create: `src/django_api_workspace/apps.py`
- Create: `src/django_api_workspace/settings.py`
- Create: `src/django_api_workspace/urls.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/settings.py`
- Create: `tests/urls.py`
- Create: `tests/test_package_import.py`

- [ ] **Step 1: Write the failing package import test**

Create `tests/test_package_import.py`:

```python
import django_api_workspace
from django_api_workspace.apps import DjangoApiWorkspaceConfig


def test_package_exposes_version():
    assert django_api_workspace.__version__ == "0.1.0"


def test_app_config_name():
    assert DjangoApiWorkspaceConfig.name == "django_api_workspace"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/test_package_import.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'django_api_workspace'`.

- [ ] **Step 3: Create the package scaffold**

Create `.gitignore`:

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
build/
dist/
*.egg-info/
db.sqlite3
```

Create `README.md`:

```markdown
# django-api-workspace

Embedded Django API documentation and testing workspace inspired by Swagger and Postman.

## Install

```bash
pip install django-api-workspace
```

Add the app and URLs:

```python
INSTALLED_APPS = [
    "django_api_workspace",
]
```

```python
from django.urls import include, path

urlpatterns = [
    path("api-workspace/", include("django_api_workspace.urls")),
]
```

Run migrations:

```bash
python manage.py migrate
python manage.py apiworkspace bootstrap
```
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "django-api-workspace"
version = "0.1.0"
description = "Embedded Django API documentation, workspace, and testing dashboard."
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
  "Django>=4.2,<6.0",
]

[project.optional-dependencies]
test = [
  "pytest>=8.0",
  "pytest-django>=4.8",
]
importers = [
  "PyYAML>=6.0",
]
runners = [
  "httpx>=0.27",
  "websockets>=12.0",
  "grpcio>=1.60",
  "protobuf>=4.25",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
django_api_workspace = [
  "templates/django_api_workspace/**/*.html",
]

[tool.pytest.ini_options]
DJANGO_SETTINGS_MODULE = "tests.settings"
pythonpath = ["src", "."]
testpaths = ["tests"]
```

Create `src/django_api_workspace/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/django_api_workspace/apps.py`:

```python
from django.apps import AppConfig


class DjangoApiWorkspaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_api_workspace"
    verbose_name = "Django API Workspace"
```

Create `src/django_api_workspace/settings.py`:

```python
from django.conf import settings


def allow_signup() -> bool:
    return bool(getattr(settings, "API_WORKSPACE_ALLOW_SIGNUP", True))


def invite_only() -> bool:
    return bool(getattr(settings, "API_WORKSPACE_INVITE_ONLY", False))


def public_docs_enabled() -> bool:
    return bool(getattr(settings, "API_WORKSPACE_PUBLIC_DOCS_ENABLED", False))


def runner_enabled() -> bool:
    return bool(getattr(settings, "API_WORKSPACE_RUNNER_ENABLED", True))


def staff_admin_enabled() -> bool:
    return bool(getattr(settings, "API_WORKSPACE_STAFF_ADMIN", False))
```

Create `src/django_api_workspace/urls.py`:

```python
from django.urls import include, path

app_name = "api_workspace"

urlpatterns = [
    path("", include("django_api_workspace.dashboard.urls")),
    path("docs/", include("django_api_workspace.docs.urls")),
]
```

Create `tests/__init__.py`:

```python
```

Create `tests/conftest.py`:

```python
import pytest


@pytest.fixture
def password():
    return "correct-horse-battery-staple"
```

Create `tests/settings.py`:

```python
SECRET_KEY = "test-secret-key"
ROOT_URLCONF = "tests.urls"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django_api_workspace",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.request",
            ],
        },
    }
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

LOGIN_URL = "/api-workspace/login/"
LOGIN_REDIRECT_URL = "/api-workspace/"
API_WORKSPACE_ALLOW_SIGNUP = True
API_WORKSPACE_PUBLIC_DOCS_ENABLED = False
API_WORKSPACE_RUNNER_ENABLED = True
```

Create `tests/urls.py`:

```python
from django.urls import include, path

urlpatterns = [
    path("api-workspace/", include("django_api_workspace.urls")),
]
```

- [ ] **Step 4: Run the package import test**

Run:

```bash
python -m pytest tests/test_package_import.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add .gitignore README.md pyproject.toml src tests
git commit -m "chore: scaffold django api workspace package"
```

---

### Task 2: Workspace Account Models

**Files:**
- Create: `src/django_api_workspace/models/__init__.py`
- Create: `src/django_api_workspace/models/workspaces.py`
- Test: `tests/test_models.py`
- Generated: `src/django_api_workspace/migrations/0001_initial.py`

- [ ] **Step 1: Write failing model tests for workspaces and membership**

Create `tests/test_models.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from django_api_workspace.models import Workspace, WorkspaceInvitation, WorkspaceMember


@pytest.mark.django_db
def test_workspace_owner_membership_is_unique():
    user = get_user_model().objects.create_user(username="owner", password="pass")
    workspace = Workspace.objects.create(
        name="Acme APIs",
        slug="acme-apis",
        created_by=user,
    )

    member = WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=WorkspaceMember.Role.OWNER,
    )

    assert str(workspace) == "Acme APIs"
    assert str(member) == "owner - Acme APIs (Owner)"
    assert workspace.memberships.count() == 1


@pytest.mark.django_db
def test_workspace_invitation_tracks_role_and_email():
    user = get_user_model().objects.create_user(username="owner", password="pass")
    workspace = Workspace.objects.create(
        name="Acme APIs",
        slug="acme-apis",
        created_by=user,
    )

    invitation = WorkspaceInvitation.objects.create(
        workspace=workspace,
        email="editor@example.com",
        role=WorkspaceMember.Role.EDITOR,
        invited_by=user,
        token="invite-token",
    )

    assert str(invitation) == "editor@example.com -> Acme APIs (Editor)"
    assert invitation.accepted_at is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: FAIL with `ImportError` for `Workspace`.

- [ ] **Step 3: Implement workspace models**

Create `src/django_api_workspace/models/workspaces.py`:

```python
from django.conf import settings
from django.db import models


class Workspace(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        TOKEN = "token", "Token protected"
        PUBLIC = "public", "Public"

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_api_workspaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class WorkspaceMember(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_workspace_memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["workspace__name", "user__username"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "user"],
                name="unique_api_workspace_member",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.workspace} ({self.get_role_display()})"


class WorkspaceInvitation(models.Model):
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=WorkspaceMember.Role.choices)
    token = models.CharField(max_length=128, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_api_workspace_invitations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} -> {self.workspace} ({self.get_role_display()})"
```

Create `src/django_api_workspace/models/__init__.py`:

```python
from django_api_workspace.models.workspaces import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
)

__all__ = [
    "Workspace",
    "WorkspaceInvitation",
    "WorkspaceMember",
]
```

- [ ] **Step 4: Generate migrations**

Run:

```bash
python -m django makemigrations django_api_workspace --settings=tests.settings
```

Expected: migration `src/django_api_workspace/migrations/0001_initial.py` is created with `Workspace`, `WorkspaceMember`, and `WorkspaceInvitation`.

- [ ] **Step 5: Run model tests**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/django_api_workspace/models src/django_api_workspace/migrations tests/test_models.py
git commit -m "feat: add workspace account models"
```

---

### Task 3: Collections, Endpoints, Documentation, And Protocol Models

**Files:**
- Modify: `src/django_api_workspace/models/__init__.py`
- Create: `src/django_api_workspace/models/apis.py`
- Modify: `tests/test_models.py`
- Generated: update `src/django_api_workspace/migrations/0001_initial.py` or create the next migration

- [ ] **Step 1: Add failing tests for API documentation models**

Append to `tests/test_models.py`:

```python
from django_api_workspace.models import (
    ApiGroup,
    Collection,
    DocumentationPage,
    Endpoint,
    Example,
    GraphQLOperation,
    GrpcOperation,
    RestOperation,
    WebSocketOperation,
)


@pytest.mark.django_db
def test_collection_group_endpoint_and_docs_models():
    user = get_user_model().objects.create_user(username="api-owner", password="pass")
    workspace = Workspace.objects.create(name="Core APIs", slug="core-apis", created_by=user)
    collection = Collection.objects.create(workspace=workspace, name="Billing", slug="billing")
    group = ApiGroup.objects.create(collection=collection, name="Invoices", slug="invoices")
    endpoint = Endpoint.objects.create(
        workspace=workspace,
        collection=collection,
        group=group,
        protocol=Endpoint.Protocol.REST,
        name="List invoices",
        slug="list-invoices",
        summary="Return invoices for the current account.",
    )
    page = DocumentationPage.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        title="Authentication",
        slug="authentication",
        body="Send a bearer token.",
    )
    example = Example.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        name="Success response",
        kind=Example.Kind.RESPONSE,
        payload={"status": 200},
        publishable=True,
    )

    assert str(collection) == "Billing"
    assert str(group) == "Invoices"
    assert str(endpoint) == "REST: List invoices"
    assert str(page) == "Authentication"
    assert str(example) == "Success response"


@pytest.mark.django_db
def test_protocol_detail_models_attach_to_endpoint():
    workspace = Workspace.objects.create(name="Protocol APIs", slug="protocol-apis")
    rest_endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.REST,
        name="Create payment",
        slug="create-payment",
    )
    graphql_endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.GRAPHQL,
        name="Get viewer",
        slug="get-viewer",
    )
    websocket_endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.WEBSOCKET,
        name="Subscribe to events",
        slug="subscribe-events",
    )
    grpc_endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.GRPC,
        name="Create invoice",
        slug="grpc-create-invoice",
    )

    rest = RestOperation.objects.create(endpoint=rest_endpoint, method="POST", path="/payments")
    graphql = GraphQLOperation.objects.create(
        endpoint=graphql_endpoint,
        operation_type=GraphQLOperation.OperationType.QUERY,
        operation_name="GetViewer",
    )
    websocket = WebSocketOperation.objects.create(
        endpoint=websocket_endpoint,
        url="wss://api.example.test/events",
    )
    grpc = GrpcOperation.objects.create(
        endpoint=grpc_endpoint,
        package="billing.v1",
        service="InvoiceService",
        method="CreateInvoice",
    )

    assert str(rest) == "POST /payments"
    assert str(graphql) == "QUERY GetViewer"
    assert str(websocket) == "wss://api.example.test/events"
    assert str(grpc) == "billing.v1.InvoiceService/CreateInvoice"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: FAIL with `ImportError` for `Collection`.

- [ ] **Step 3: Implement API documentation and protocol models**

Create `src/django_api_workspace/models/apis.py`:

```python
from django.db import models

from django_api_workspace.models.workspaces import Workspace


class Collection(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="collections")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_api_collection_slug_per_workspace",
            )
        ]

    def __str__(self) -> str:
        return self.name


class ApiGroup(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name="groups")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "parent", "slug"],
                name="unique_api_group_slug_per_parent",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Endpoint(models.Model):
    class Protocol(models.TextChoices):
        REST = "rest", "REST"
        GRAPHQL = "graphql", "GraphQL"
        WEBSOCKET = "websocket", "WebSocket"
        GRPC = "grpc", "gRPC"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        INTERNAL = "internal", "Internal"
        TOKEN = "token", "Token protected"
        PUBLIC = "public", "Public"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="endpoints")
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="endpoints",
    )
    group = models.ForeignKey(
        ApiGroup,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="endpoints",
    )
    protocol = models.CharField(max_length=20, choices=Protocol.choices)
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    summary = models.TextField(blank=True)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE)
    position = models.PositiveIntegerField(default=0)
    archived_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["collection__position", "group__position", "position", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_api_endpoint_slug_per_workspace",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_protocol_display()}: {self.name}"


class DocumentationPage(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="documentation_pages")
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="documentation_pages",
    )
    group = models.ForeignKey(
        ApiGroup,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="documentation_pages",
    )
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="documentation_pages",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    body = models.TextField()
    position = models.PositiveIntegerField(default=0)
    publishable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "title"]

    def __str__(self) -> str:
        return self.title


class Example(models.Model):
    class Kind(models.TextChoices):
        REQUEST = "request", "Request"
        RESPONSE = "response", "Response"
        MESSAGE = "message", "Message"
        SCHEMA = "schema", "Schema"
        FLOW = "flow", "Flow"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="examples")
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="examples",
    )
    name = models.CharField(max_length=180)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    description = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    publishable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RestOperation(models.Model):
    endpoint = models.OneToOneField(Endpoint, on_delete=models.CASCADE, related_name="rest")
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=500)
    query_schema = models.JSONField(default=dict, blank=True)
    header_schema = models.JSONField(default=dict, blank=True)
    request_body_schema = models.JSONField(default=dict, blank=True)
    response_schemas = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"{self.method.upper()} {self.path}"


class GraphQLOperation(models.Model):
    class OperationType(models.TextChoices):
        QUERY = "query", "Query"
        MUTATION = "mutation", "Mutation"
        SUBSCRIPTION = "subscription", "Subscription"

    endpoint = models.OneToOneField(Endpoint, on_delete=models.CASCADE, related_name="graphql")
    operation_type = models.CharField(max_length=20, choices=OperationType.choices)
    operation_name = models.CharField(max_length=180, blank=True)
    query_text = models.TextField(blank=True)
    variables_schema = models.JSONField(default=dict, blank=True)
    schema_reference = models.TextField(blank=True)

    def __str__(self) -> str:
        name = self.operation_name or "Unnamed operation"
        return f"{self.operation_type.upper()} {name}"


class WebSocketOperation(models.Model):
    endpoint = models.OneToOneField(Endpoint, on_delete=models.CASCADE, related_name="websocket")
    url = models.CharField(max_length=500)
    handshake_headers = models.JSONField(default=dict, blank=True)
    message_definitions = models.JSONField(default=dict, blank=True)
    flow_definition = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return self.url


class GrpcOperation(models.Model):
    class StreamingMode(models.TextChoices):
        UNARY = "unary", "Unary"
        SERVER = "server_streaming", "Server streaming"
        CLIENT = "client_streaming", "Client streaming"
        BIDIRECTIONAL = "bidirectional_streaming", "Bidirectional streaming"

    endpoint = models.OneToOneField(Endpoint, on_delete=models.CASCADE, related_name="grpc")
    package = models.CharField(max_length=180, blank=True)
    service = models.CharField(max_length=180)
    method = models.CharField(max_length=180)
    streaming_mode = models.CharField(
        max_length=40,
        choices=StreamingMode.choices,
        default=StreamingMode.UNARY,
    )
    request_message_schema = models.JSONField(default=dict, blank=True)
    response_message_schema = models.JSONField(default=dict, blank=True)
    metadata_schema = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        package_prefix = f"{self.package}." if self.package else ""
        return f"{package_prefix}{self.service}/{self.method}"
```

Modify `src/django_api_workspace/models/__init__.py`:

```python
from django_api_workspace.models.apis import (
    ApiGroup,
    Collection,
    DocumentationPage,
    Endpoint,
    Example,
    GraphQLOperation,
    GrpcOperation,
    RestOperation,
    WebSocketOperation,
)
from django_api_workspace.models.workspaces import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
)

__all__ = [
    "ApiGroup",
    "Collection",
    "DocumentationPage",
    "Endpoint",
    "Example",
    "GraphQLOperation",
    "GrpcOperation",
    "RestOperation",
    "WebSocketOperation",
    "Workspace",
    "WorkspaceInvitation",
    "WorkspaceMember",
]
```

- [ ] **Step 4: Generate migrations**

Run:

```bash
python -m django makemigrations django_api_workspace --settings=tests.settings
```

Expected: migration includes `Collection`, `ApiGroup`, `Endpoint`, `DocumentationPage`, `Example`, and the four protocol operation models.

- [ ] **Step 5: Run model tests**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: PASS with `4 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/django_api_workspace/models src/django_api_workspace/migrations tests/test_models.py
git commit -m "feat: add protocol-aware api documentation models"
```

---

### Task 4: Runtime, Job, And Audit Models

**Files:**
- Modify: `src/django_api_workspace/models/__init__.py`
- Create: `src/django_api_workspace/models/runtime.py`
- Create: `src/django_api_workspace/models/jobs.py`
- Create: `src/django_api_workspace/models/audit.py`
- Modify: `tests/test_models.py`
- Generated: update migrations

- [ ] **Step 1: Add failing tests for runtime, jobs, and audit records**

Append to `tests/test_models.py`:

```python
from django_api_workspace.models import (
    Assertion,
    AuditLog,
    AuthProfile,
    DiscoverySnapshot,
    Environment,
    ExportJob,
    ImportJob,
    RequestHistory,
    RequestTemplate,
    SavedResponse,
    TestRun,
    TestSuite,
    Variable,
)


@pytest.mark.django_db
def test_runtime_models_capture_environment_auth_and_history():
    workspace = Workspace.objects.create(name="Runtime APIs", slug="runtime-apis")
    endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.REST,
        name="Health",
        slug="health",
    )
    environment = Environment.objects.create(workspace=workspace, name="Production", slug="production")
    variable = Variable.objects.create(
        environment=environment,
        key="token",
        value="secret-token",
        is_secret=True,
    )
    auth = AuthProfile.objects.create(
        workspace=workspace,
        name="Bearer auth",
        kind=AuthProfile.Kind.BEARER,
        config={"token": "{{token}}"},
    )
    template = RequestTemplate.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        name="Health check",
        protocol=Endpoint.Protocol.REST,
        request_config={"method": "GET", "url": "{{base_url}}/health"},
    )
    history = RequestHistory.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        environment=environment,
        request_config=template.request_config,
        response_data={"status_code": 200},
        duration_ms=32,
    )
    saved = SavedResponse.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        name="Healthy",
        response_data=history.response_data,
    )

    assert str(environment) == "Production"
    assert str(variable) == "token"
    assert variable.masked_value == "********"
    assert str(auth) == "Bearer auth"
    assert str(template) == "Health check"
    assert str(history) == "REST request to Health"
    assert str(saved) == "Healthy"


@pytest.mark.django_db
def test_tests_jobs_and_audit_models_have_readable_names():
    user = get_user_model().objects.create_user(username="auditor", password="pass")
    workspace = Workspace.objects.create(name="Quality APIs", slug="quality-apis", created_by=user)
    endpoint = Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.GRAPHQL,
        name="Viewer",
        slug="viewer",
    )
    assertion = Assertion.objects.create(
        workspace=workspace,
        endpoint=endpoint,
        name="No GraphQL errors",
        kind=Assertion.Kind.JSON_PATH,
        expression="$.errors",
        expected={"exists": False},
    )
    suite = TestSuite.objects.create(workspace=workspace, name="Smoke")
    suite.assertions.add(assertion)
    run = TestRun.objects.create(workspace=workspace, suite=suite, status=TestRun.Status.PASSED)
    import_job = ImportJob.objects.create(workspace=workspace, kind=ImportJob.Kind.OPENAPI, status=ImportJob.Status.PENDING)
    export_job = ExportJob.objects.create(workspace=workspace, kind=ExportJob.Kind.STATIC_DOCS, status=ExportJob.Status.PENDING)
    snapshot = DiscoverySnapshot.objects.create(workspace=workspace, source=DiscoverySnapshot.Source.DJANGO, summary={"added": 1})
    audit = AuditLog.objects.create(
        workspace=workspace,
        actor=user,
        action="endpoint.created",
        target_type="Endpoint",
        target_id=str(endpoint.pk),
        after={"name": endpoint.name},
    )

    assert str(assertion) == "No GraphQL errors"
    assert str(suite) == "Smoke"
    assert str(run) == "Smoke - Passed"
    assert str(import_job) == "OpenAPI import - Pending"
    assert str(export_job) == "Static docs export - Pending"
    assert str(snapshot) == "Django discovery snapshot"
    assert str(audit) == "endpoint.created Endpoint"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: FAIL with `ImportError` for `Environment`.

- [ ] **Step 3: Implement runtime models**

Create `src/django_api_workspace/models/runtime.py`:

```python
from django.db import models

from django_api_workspace.models.apis import Endpoint
from django_api_workspace.models.workspaces import Workspace


class Environment(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="environments")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    base_url = models.URLField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="unique_api_environment_slug_per_workspace",
            )
        ]

    def __str__(self) -> str:
        return self.name


class Variable(models.Model):
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name="variables")
    key = models.CharField(max_length=120)
    value = models.TextField(blank=True)
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["environment", "key"],
                name="unique_api_variable_key_per_environment",
            )
        ]

    @property
    def masked_value(self) -> str:
        return "********" if self.is_secret and self.value else self.value

    def __str__(self) -> str:
        return self.key


class AuthProfile(models.Model):
    class Kind(models.TextChoices):
        NONE = "none", "No auth"
        BEARER = "bearer", "Bearer token"
        BASIC = "basic", "Basic auth"
        API_KEY = "api_key", "API key"
        OAUTH = "oauth", "OAuth"
        CUSTOM = "custom", "Custom"
        GRPC_METADATA = "grpc_metadata", "gRPC metadata"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="auth_profiles")
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=40, choices=Kind.choices)
    config = models.JSONField(default=dict, blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RequestTemplate(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="request_templates")
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="request_templates",
    )
    name = models.CharField(max_length=180)
    protocol = models.CharField(max_length=20, choices=Endpoint.Protocol.choices)
    request_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class RequestHistory(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="request_history")
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="request_history",
    )
    environment = models.ForeignKey(
        Environment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="request_history",
    )
    protocol = models.CharField(max_length=20, choices=Endpoint.Protocol.choices, blank=True)
    request_config = models.JSONField(default=dict, blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.protocol and self.endpoint_id:
            self.protocol = self.endpoint.protocol
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        endpoint_name = self.endpoint.name if self.endpoint else "Ad hoc"
        protocol = self.get_protocol_display() if self.protocol else "Unknown"
        return f"{protocol} request to {endpoint_name}"


class SavedResponse(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="saved_responses")
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="saved_responses",
    )
    name = models.CharField(max_length=180)
    response_data = models.JSONField(default=dict, blank=True)
    publishable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Assertion(models.Model):
    class Kind(models.TextChoices):
        STATUS = "status", "Status"
        HEADER = "header", "Header"
        JSON_PATH = "json_path", "JSON path"
        BODY = "body", "Body"
        SCHEMA = "schema", "Schema"
        RESPONSE_TIME = "response_time", "Response time"
        EVENT_SEQUENCE = "event_sequence", "Event sequence"
        GRPC_STATUS = "grpc_status", "gRPC status"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="assertions")
    endpoint = models.ForeignKey(
        Endpoint,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="assertions",
    )
    name = models.CharField(max_length=180)
    kind = models.CharField(max_length=40, choices=Kind.choices)
    expression = models.TextField(blank=True)
    expected = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TestSuite(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="test_suites")
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    assertions = models.ManyToManyField(Assertion, blank=True, related_name="test_suites")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TestRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        ERROR = "error", "Error"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="test_runs")
    suite = models.ForeignKey(
        TestSuite,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="runs",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    results = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        suite_name = self.suite.name if self.suite else "Ad hoc"
        return f"{suite_name} - {self.get_status_display()}"
```

- [ ] **Step 4: Implement job and audit models**

Create `src/django_api_workspace/models/jobs.py`:

```python
from django.db import models

from django_api_workspace.models.workspaces import Workspace


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ImportJob(models.Model):
    class Kind(models.TextChoices):
        OPENAPI = "openapi", "OpenAPI"
        GRAPHQL = "graphql", "GraphQL"
        PROTO = "proto", "Proto"
        WEBSOCKET = "websocket", "WebSocket"

    Status = JobStatus

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="import_jobs")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    source_name = models.CharField(max_length=255, blank=True)
    input_payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} import - {self.get_status_display()}"


class ExportJob(models.Model):
    class Kind(models.TextChoices):
        STATIC_DOCS = "static_docs", "Static docs"
        OPENAPI = "openapi", "OpenAPI"
        GRAPHQL = "graphql", "GraphQL"
        PROTO_REFERENCE = "proto_reference", "Proto reference"
        JSON_PROJECT = "json_project", "JSON project"

    Status = JobStatus

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="export_jobs")
    kind = models.CharField(max_length=40, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    output_path = models.CharField(max_length=500, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_log = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} export - {self.get_status_display()}"


class DiscoverySnapshot(models.Model):
    class Source(models.TextChoices):
        DJANGO = "django", "Django"
        DRF = "drf", "Django REST Framework"
        GRAPHQL = "graphql", "GraphQL"
        CHANNELS = "channels", "Channels"
        GRPC = "grpc", "gRPC"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="discovery_snapshots")
    source = models.CharField(max_length=30, choices=Source.choices)
    summary = models.JSONField(default=dict, blank=True)
    discovered_items = models.JSONField(default=list, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_source_display()} discovery snapshot"
```

Create `src/django_api_workspace/models/audit.py`:

```python
from django.conf import settings
from django.db import models

from django_api_workspace.models.workspaces import Workspace


class AuditLog(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="audit_logs")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="api_workspace_audit_logs",
    )
    action = models.CharField(max_length=120)
    target_type = models.CharField(max_length=120)
    target_id = models.CharField(max_length=120, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}"
```

- [ ] **Step 5: Export runtime, job, and audit models**

Modify `src/django_api_workspace/models/__init__.py`:

```python
from django_api_workspace.models.apis import (
    ApiGroup,
    Collection,
    DocumentationPage,
    Endpoint,
    Example,
    GraphQLOperation,
    GrpcOperation,
    RestOperation,
    WebSocketOperation,
)
from django_api_workspace.models.audit import AuditLog
from django_api_workspace.models.jobs import DiscoverySnapshot, ExportJob, ImportJob
from django_api_workspace.models.runtime import (
    Assertion,
    AuthProfile,
    Environment,
    RequestHistory,
    RequestTemplate,
    SavedResponse,
    TestRun,
    TestSuite,
    Variable,
)
from django_api_workspace.models.workspaces import (
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
)

__all__ = [
    "ApiGroup",
    "Assertion",
    "AuditLog",
    "AuthProfile",
    "Collection",
    "DiscoverySnapshot",
    "DocumentationPage",
    "Endpoint",
    "Environment",
    "Example",
    "ExportJob",
    "GraphQLOperation",
    "GrpcOperation",
    "ImportJob",
    "RequestHistory",
    "RequestTemplate",
    "RestOperation",
    "SavedResponse",
    "TestRun",
    "TestSuite",
    "Variable",
    "WebSocketOperation",
    "Workspace",
    "WorkspaceInvitation",
    "WorkspaceMember",
]
```

- [ ] **Step 6: Generate migrations**

Run:

```bash
python -m django makemigrations django_api_workspace --settings=tests.settings
```

Expected: migration includes `Environment`, `Variable`, `AuthProfile`, `RequestTemplate`, `RequestHistory`, `SavedResponse`, `Assertion`, `TestSuite`, `TestRun`, `ImportJob`, `ExportJob`, `DiscoverySnapshot`, and `AuditLog`.

- [ ] **Step 7: Run model tests**

Run:

```bash
python -m pytest tests/test_models.py -q
```

Expected: PASS with `6 passed`.

- [ ] **Step 8: Commit**

Run:

```bash
git add src/django_api_workspace/models src/django_api_workspace/migrations tests/test_models.py
git commit -m "feat: add workspace runtime and audit models"
```

---

### Task 5: Workspace Permission And Creation Services

**Files:**
- Create: `src/django_api_workspace/core/__init__.py`
- Create: `src/django_api_workspace/core/permissions.py`
- Create: `src/django_api_workspace/core/services.py`
- Create: `tests/test_permissions.py`

- [ ] **Step 1: Write failing permission and service tests**

Create `tests/test_permissions.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from django_api_workspace.core.permissions import WorkspaceAction, user_can
from django_api_workspace.core.services import create_workspace_for_user
from django_api_workspace.models import WorkspaceMember


@pytest.mark.django_db
def test_create_workspace_for_user_assigns_owner_role():
    user = get_user_model().objects.create_user(username="founder", password="pass")

    workspace = create_workspace_for_user(user=user, name="Founder APIs")

    member = workspace.memberships.get(user=user)
    assert workspace.slug == "founder-apis"
    assert member.role == WorkspaceMember.Role.OWNER


@pytest.mark.django_db
def test_workspace_role_permissions():
    owner = get_user_model().objects.create_user(username="owner", password="pass")
    editor = get_user_model().objects.create_user(username="editor", password="pass")
    viewer = get_user_model().objects.create_user(username="viewer", password="pass")
    workspace = create_workspace_for_user(user=owner, name="Role APIs")
    WorkspaceMember.objects.create(workspace=workspace, user=editor, role=WorkspaceMember.Role.EDITOR)
    WorkspaceMember.objects.create(workspace=workspace, user=viewer, role=WorkspaceMember.Role.VIEWER)

    assert user_can(owner, workspace, WorkspaceAction.MANAGE_MEMBERS) is True
    assert user_can(editor, workspace, WorkspaceAction.EDIT) is True
    assert user_can(editor, workspace, WorkspaceAction.MANAGE_MEMBERS) is False
    assert user_can(viewer, workspace, WorkspaceAction.VIEW) is True
    assert user_can(viewer, workspace, WorkspaceAction.EDIT) is False


@pytest.mark.django_db
def test_anonymous_user_cannot_access_workspace():
    workspace = create_workspace_for_user(
        user=get_user_model().objects.create_user(username="owner", password="pass"),
        name="Private APIs",
    )

    class AnonymousUser:
        is_authenticated = False
        is_staff = False

    assert user_can(AnonymousUser(), workspace, WorkspaceAction.VIEW) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_permissions.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `django_api_workspace.core.permissions`.

- [ ] **Step 3: Implement permission checks**

Create `src/django_api_workspace/core/__init__.py`:

```python
```

Create `src/django_api_workspace/core/permissions.py`:

```python
from enum import Enum

from django_api_workspace import settings as package_settings
from django_api_workspace.models import Workspace, WorkspaceMember


class WorkspaceAction(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    RUN_REQUESTS = "run_requests"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_SETTINGS = "manage_settings"
    DELETE_WORKSPACE = "delete_workspace"


ROLE_PERMISSIONS = {
    WorkspaceMember.Role.OWNER: {
        WorkspaceAction.VIEW,
        WorkspaceAction.EDIT,
        WorkspaceAction.RUN_REQUESTS,
        WorkspaceAction.MANAGE_MEMBERS,
        WorkspaceAction.MANAGE_SETTINGS,
        WorkspaceAction.DELETE_WORKSPACE,
    },
    WorkspaceMember.Role.ADMIN: {
        WorkspaceAction.VIEW,
        WorkspaceAction.EDIT,
        WorkspaceAction.RUN_REQUESTS,
        WorkspaceAction.MANAGE_MEMBERS,
        WorkspaceAction.MANAGE_SETTINGS,
    },
    WorkspaceMember.Role.EDITOR: {
        WorkspaceAction.VIEW,
        WorkspaceAction.EDIT,
        WorkspaceAction.RUN_REQUESTS,
    },
    WorkspaceMember.Role.VIEWER: {
        WorkspaceAction.VIEW,
    },
}


def user_can(user, workspace: Workspace, action: WorkspaceAction) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) and package_settings.staff_admin_enabled():
        return True
    try:
        membership = WorkspaceMember.objects.get(workspace=workspace, user=user)
    except WorkspaceMember.DoesNotExist:
        return False
    return action in ROLE_PERMISSIONS[membership.role]
```

- [ ] **Step 4: Implement workspace creation service**

Create `src/django_api_workspace/core/services.py`:

```python
from django.db import transaction
from django.utils.text import slugify

from django_api_workspace.models import Workspace, WorkspaceMember


def _unique_workspace_slug(base_slug: str) -> str:
    slug = base_slug or "workspace"
    candidate = slug
    suffix = 2
    while Workspace.objects.filter(slug=candidate).exists():
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


@transaction.atomic
def create_workspace_for_user(*, user, name: str, description: str = "") -> Workspace:
    workspace = Workspace.objects.create(
        name=name,
        slug=_unique_workspace_slug(slugify(name)),
        description=description,
        created_by=user,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=WorkspaceMember.Role.OWNER,
    )
    return workspace
```

- [ ] **Step 5: Run permission tests**

Run:

```bash
python -m pytest tests/test_permissions.py -q
```

Expected: PASS with `3 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/django_api_workspace/core tests/test_permissions.py
git commit -m "feat: add workspace permission services"
```

---

### Task 6: Authenticated Dashboard Entry Points

**Files:**
- Create: `src/django_api_workspace/accounts/__init__.py`
- Create: `src/django_api_workspace/accounts/forms.py`
- Create: `src/django_api_workspace/accounts/views.py`
- Create: `src/django_api_workspace/dashboard/__init__.py`
- Create: `src/django_api_workspace/dashboard/urls.py`
- Create: `src/django_api_workspace/dashboard/views.py`
- Create: `src/django_api_workspace/templates/django_api_workspace/base.html`
- Create: `src/django_api_workspace/templates/django_api_workspace/accounts/login.html`
- Create: `src/django_api_workspace/templates/django_api_workspace/accounts/register.html`
- Create: `src/django_api_workspace/templates/django_api_workspace/dashboard/home.html`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing dashboard auth tests**

Create `tests/test_dashboard.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from django_api_workspace.models import Workspace, WorkspaceMember


@pytest.mark.django_db
def test_dashboard_requires_login(client):
    response = client.get(reverse("api_workspace:dashboard"))

    assert response.status_code == 302
    assert "/api-workspace/login/" in response["Location"]


@pytest.mark.django_db
def test_logged_in_user_sees_owned_workspace(client):
    user = get_user_model().objects.create_user(username="owner", password="pass")
    workspace = Workspace.objects.create(name="Owned APIs", slug="owned-apis", created_by=user)
    WorkspaceMember.objects.create(workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER)
    client.force_login(user)

    response = client.get(reverse("api_workspace:dashboard"))

    assert response.status_code == 200
    assert b"Owned APIs" in response.content


@pytest.mark.django_db
def test_register_view_creates_user_and_logs_in(client, password):
    response = client.post(
        reverse("api_workspace:register"),
        {
            "username": "new-user",
            "email": "new@example.com",
            "password1": password,
            "password2": password,
        },
        follow=True,
    )

    assert response.status_code == 200
    assert get_user_model().objects.filter(username="new-user").exists()
    assert b"Your workspaces" in response.content
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_dashboard.py -q
```

Expected: FAIL because `django_api_workspace.dashboard.urls` does not exist.

- [ ] **Step 3: Implement account form and registration view**

Create `src/django_api_workspace/accounts/__init__.py`:

```python
```

Create `src/django_api_workspace/accounts/forms.py`:

```python
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django import forms


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = get_user_model()
        fields = ("username", "email")
```

Create `src/django_api_workspace/accounts/views.py`:

```python
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.views.generic import CreateView

from django_api_workspace.accounts.forms import RegisterForm


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "django_api_workspace/accounts/register.html"
    success_url = reverse_lazy("api_workspace:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
```

- [ ] **Step 4: Implement dashboard URLs and home view**

Create `src/django_api_workspace/dashboard/__init__.py`:

```python
```

Create `src/django_api_workspace/dashboard/views.py`:

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from django_api_workspace.models import Workspace


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "django_api_workspace/dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspaces"] = (
            Workspace.objects.filter(memberships__user=self.request.user)
            .distinct()
            .order_by("name")
        )
        return context
```

Create `src/django_api_workspace/dashboard/urls.py`:

```python
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from django_api_workspace.accounts.views import RegisterView
from django_api_workspace.dashboard.views import DashboardHomeView

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="dashboard"),
    path(
        "login/",
        LoginView.as_view(template_name="django_api_workspace/accounts/login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
]
```

- [ ] **Step 5: Implement base and account templates**

Create `src/django_api_workspace/templates/django_api_workspace/base.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}API Workspace{% endblock %}</title>
  </head>
  <body>
    <header>
      <a href="{% url 'api_workspace:dashboard' %}">API Workspace</a>
      <nav>
        {% if request.user.is_authenticated %}
          <span>{{ request.user.username }}</span>
          <form method="post" action="{% url 'api_workspace:logout' %}">
            {% csrf_token %}
            <button type="submit">Log out</button>
          </form>
        {% else %}
          <a href="{% url 'api_workspace:login' %}">Log in</a>
          <a href="{% url 'api_workspace:register' %}">Register</a>
        {% endif %}
      </nav>
    </header>
    <main>
      {% block content %}{% endblock %}
    </main>
  </body>
</html>
```

Create `src/django_api_workspace/templates/django_api_workspace/accounts/login.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}Log in | API Workspace{% endblock %}

{% block content %}
  <h1>Log in</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Log in</button>
  </form>
{% endblock %}
```

Create `src/django_api_workspace/templates/django_api_workspace/accounts/register.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}Register | API Workspace{% endblock %}

{% block content %}
  <h1>Create your dashboard account</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Create account</button>
  </form>
{% endblock %}
```

Create `src/django_api_workspace/templates/django_api_workspace/dashboard/home.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}Your workspaces | API Workspace{% endblock %}

{% block content %}
  <h1>Your workspaces</h1>
  <p>Create, document, test, and publish APIs from your dashboard.</p>
  <a href="{% url 'api_workspace:workspace_create' %}">New workspace</a>

  {% if workspaces %}
    <ul>
      {% for workspace in workspaces %}
        <li>
          <a href="{% url 'api_workspace:workspace_detail' workspace.slug %}">{{ workspace.name }}</a>
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No workspaces yet.</p>
  {% endif %}
{% endblock %}
```

- [ ] **Step 6: Run dashboard tests and capture the next expected failures**

Run:

```bash
python -m pytest tests/test_dashboard.py -q
```

Expected: FAIL with `NoReverseMatch` for `workspace_create`, because workspace create/detail views are added in Task 7.

- [ ] **Step 7: Commit the working auth foundation after Task 7 adds missing routes**

Do not commit this task yet. Task 7 completes the route names referenced by the dashboard template.

---

### Task 7: Dashboard Workspace, Collection, And Endpoint CRUD

**Files:**
- Create: `src/django_api_workspace/dashboard/forms.py`
- Modify: `src/django_api_workspace/dashboard/views.py`
- Modify: `src/django_api_workspace/dashboard/urls.py`
- Create: `src/django_api_workspace/templates/django_api_workspace/dashboard/workspace_form.html`
- Create: `src/django_api_workspace/templates/django_api_workspace/dashboard/workspace_detail.html`
- Create: `src/django_api_workspace/templates/django_api_workspace/dashboard/endpoint_form.html`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Add failing CRUD tests**

Append to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_user_can_create_workspace_from_dashboard(client):
    user = get_user_model().objects.create_user(username="creator", password="pass")
    client.force_login(user)

    response = client.post(
        reverse("api_workspace:workspace_create"),
        {"name": "Payments APIs", "description": "Payment docs"},
        follow=True,
    )

    workspace = Workspace.objects.get(slug="payments-apis")
    assert response.status_code == 200
    assert workspace.memberships.get(user=user).role == WorkspaceMember.Role.OWNER
    assert b"Payments APIs" in response.content


@pytest.mark.django_db
def test_workspace_owner_can_create_collection_and_endpoint(client):
    user = get_user_model().objects.create_user(username="owner2", password="pass")
    workspace = Workspace.objects.create(name="Product APIs", slug="product-apis", created_by=user)
    WorkspaceMember.objects.create(workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER)
    client.force_login(user)

    collection_response = client.post(
        reverse("api_workspace:collection_create", args=[workspace.slug]),
        {"name": "Catalog", "slug": "catalog", "description": "Catalog APIs"},
        follow=True,
    )
    endpoint_response = client.post(
        reverse("api_workspace:endpoint_create", args=[workspace.slug]),
        {
            "collection": workspace.collections.get(slug="catalog").pk,
            "group": "",
            "protocol": "rest",
            "name": "List products",
            "slug": "list-products",
            "summary": "List visible products.",
            "description": "Returns product cards.",
            "visibility": "private",
        },
        follow=True,
    )

    assert collection_response.status_code == 200
    assert endpoint_response.status_code == 200
    assert workspace.endpoints.filter(slug="list-products").exists()
    assert b"List products" in endpoint_response.content


@pytest.mark.django_db
def test_non_member_cannot_open_private_workspace(client):
    owner = get_user_model().objects.create_user(username="private-owner", password="pass")
    outsider = get_user_model().objects.create_user(username="outsider", password="pass")
    workspace = Workspace.objects.create(name="Private APIs", slug="private-apis", created_by=owner)
    WorkspaceMember.objects.create(workspace=workspace, user=owner, role=WorkspaceMember.Role.OWNER)
    client.force_login(outsider)

    response = client.get(reverse("api_workspace:workspace_detail", args=[workspace.slug]))

    assert response.status_code == 404
```

- [ ] **Step 2: Run dashboard tests to verify they fail**

Run:

```bash
python -m pytest tests/test_dashboard.py -q
```

Expected: FAIL with `NoReverseMatch` for `workspace_create`.

- [ ] **Step 3: Implement dashboard forms**

Create `src/django_api_workspace/dashboard/forms.py`:

```python
from django import forms

from django_api_workspace.models import Collection, Endpoint, Workspace


class WorkspaceForm(forms.ModelForm):
    class Meta:
        model = Workspace
        fields = ["name", "description"]


class CollectionForm(forms.ModelForm):
    class Meta:
        model = Collection
        fields = ["name", "slug", "description"]


class EndpointForm(forms.ModelForm):
    class Meta:
        model = Endpoint
        fields = [
            "collection",
            "group",
            "protocol",
            "name",
            "slug",
            "summary",
            "description",
            "visibility",
        ]

    def __init__(self, *args, workspace, **kwargs):
        super().__init__(*args, **kwargs)
        self.workspace = workspace
        self.fields["collection"].queryset = workspace.collections.order_by("name")
        self.fields["group"].queryset = workspace.collections.none()
        if self.data.get("collection"):
            self.fields["group"].queryset = workspace.collections.get(
                pk=self.data["collection"]
            ).groups.order_by("name")
        self.fields["collection"].required = False
        self.fields["group"].required = False
```

- [ ] **Step 4: Implement dashboard CRUD views**

Modify `src/django_api_workspace/dashboard/views.py`:

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, DetailView, TemplateView

from django_api_workspace.core.permissions import WorkspaceAction, user_can
from django_api_workspace.core.services import create_workspace_for_user
from django_api_workspace.dashboard.forms import CollectionForm, EndpointForm, WorkspaceForm
from django_api_workspace.models import Collection, Endpoint, Workspace


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = "django_api_workspace/dashboard/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["workspaces"] = (
            Workspace.objects.filter(memberships__user=self.request.user)
            .distinct()
            .order_by("name")
        )
        return context


class WorkspaceCreateView(LoginRequiredMixin, CreateView):
    form_class = WorkspaceForm
    template_name = "django_api_workspace/dashboard/workspace_form.html"

    def form_valid(self, form):
        self.object = create_workspace_for_user(
            user=self.request.user,
            name=form.cleaned_data["name"],
            description=form.cleaned_data["description"],
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("api_workspace:workspace_detail", args=[self.object.slug])


class WorkspaceDetailView(LoginRequiredMixin, DetailView):
    model = Workspace
    slug_field = "slug"
    slug_url_kwarg = "workspace_slug"
    template_name = "django_api_workspace/dashboard/workspace_detail.html"

    def get_object(self, queryset=None):
        workspace = super().get_object(queryset)
        if not user_can(self.request.user, workspace, WorkspaceAction.VIEW):
            raise Http404("Workspace not found")
        return workspace


class WorkspaceObjectMixin(LoginRequiredMixin):
    workspace_slug_url_kwarg = "workspace_slug"

    def dispatch(self, request, *args, **kwargs):
        self.workspace = get_object_or_404(Workspace, slug=kwargs[self.workspace_slug_url_kwarg])
        if not user_can(request.user, self.workspace, WorkspaceAction.EDIT):
            raise Http404("Workspace not found")
        return super().dispatch(request, *args, **kwargs)


class CollectionCreateView(WorkspaceObjectMixin, CreateView):
    model = Collection
    form_class = CollectionForm
    template_name = "django_api_workspace/dashboard/workspace_form.html"

    def form_valid(self, form):
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("api_workspace:workspace_detail", args=[self.workspace.slug])


class EndpointCreateView(WorkspaceObjectMixin, CreateView):
    model = Endpoint
    form_class = EndpointForm
    template_name = "django_api_workspace/dashboard/endpoint_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["workspace"] = self.workspace
        return kwargs

    def form_valid(self, form):
        form.instance.workspace = self.workspace
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("api_workspace:workspace_detail", args=[self.workspace.slug])
```

- [ ] **Step 5: Implement dashboard URLs**

Modify `src/django_api_workspace/dashboard/urls.py`:

```python
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from django_api_workspace.accounts.views import RegisterView
from django_api_workspace.dashboard.views import (
    CollectionCreateView,
    DashboardHomeView,
    EndpointCreateView,
    WorkspaceCreateView,
    WorkspaceDetailView,
)

urlpatterns = [
    path("", DashboardHomeView.as_view(), name="dashboard"),
    path(
        "login/",
        LoginView.as_view(template_name="django_api_workspace/accounts/login.html"),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("workspaces/new/", WorkspaceCreateView.as_view(), name="workspace_create"),
    path("workspaces/<slug:workspace_slug>/", WorkspaceDetailView.as_view(), name="workspace_detail"),
    path(
        "workspaces/<slug:workspace_slug>/collections/new/",
        CollectionCreateView.as_view(),
        name="collection_create",
    ),
    path(
        "workspaces/<slug:workspace_slug>/endpoints/new/",
        EndpointCreateView.as_view(),
        name="endpoint_create",
    ),
]
```

- [ ] **Step 6: Implement dashboard CRUD templates**

Create `src/django_api_workspace/templates/django_api_workspace/dashboard/workspace_form.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}Workspace form | API Workspace{% endblock %}

{% block content %}
  <h1>{% if object %}Edit workspace{% else %}New workspace{% endif %}</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Save</button>
  </form>
{% endblock %}
```

Create `src/django_api_workspace/templates/django_api_workspace/dashboard/workspace_detail.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}{{ object.name }} | API Workspace{% endblock %}

{% block content %}
  <h1>{{ object.name }}</h1>
  <p>{{ object.description }}</p>

  <nav>
    <a href="{% url 'api_workspace:collection_create' object.slug %}">New collection</a>
    <a href="{% url 'api_workspace:endpoint_create' object.slug %}">New endpoint</a>
  </nav>

  <section>
    <h2>Collections</h2>
    {% if object.collections.exists %}
      <ul>
        {% for collection in object.collections.all %}
          <li>{{ collection.name }}</li>
        {% endfor %}
      </ul>
    {% else %}
      <p>No collections yet.</p>
    {% endif %}
  </section>

  <section>
    <h2>Endpoints</h2>
    {% if object.endpoints.exists %}
      <ul>
        {% for endpoint in object.endpoints.all %}
          <li>{{ endpoint.get_protocol_display }}: {{ endpoint.name }}</li>
        {% endfor %}
      </ul>
    {% else %}
      <p>No endpoints yet.</p>
    {% endif %}
  </section>
{% endblock %}
```

Create `src/django_api_workspace/templates/django_api_workspace/dashboard/endpoint_form.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}New endpoint | API Workspace{% endblock %}

{% block content %}
  <h1>New endpoint</h1>
  <form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit">Save endpoint</button>
  </form>
{% endblock %}
```

- [ ] **Step 7: Run dashboard tests**

Run:

```bash
python -m pytest tests/test_dashboard.py -q
```

Expected: PASS with `6 passed`.

- [ ] **Step 8: Commit Tasks 6 and 7 together**

Run:

```bash
git add src/django_api_workspace/accounts src/django_api_workspace/dashboard src/django_api_workspace/templates tests/test_dashboard.py
git commit -m "feat: add authenticated workspace dashboard"
```

---

### Task 8: Private-By-Default Public Docs

**Files:**
- Create: `src/django_api_workspace/docs/__init__.py`
- Create: `src/django_api_workspace/docs/views.py`
- Create: `src/django_api_workspace/docs/urls.py`
- Create: `src/django_api_workspace/templates/django_api_workspace/docs/workspace_public.html`
- Create: `tests/test_public_docs.py`

- [ ] **Step 1: Write failing public docs tests**

Create `tests/test_public_docs.py`:

```python
import pytest
from django.test import override_settings
from django.urls import reverse

from django_api_workspace.models import Endpoint, Workspace


@pytest.mark.django_db
def test_public_docs_are_disabled_by_default(client):
    workspace = Workspace.objects.create(name="Public APIs", slug="public-apis", visibility=Workspace.Visibility.PUBLIC)

    response = client.get(reverse("api_workspace:public_workspace_docs", args=[workspace.slug]))

    assert response.status_code == 404


@pytest.mark.django_db
@override_settings(API_WORKSPACE_PUBLIC_DOCS_ENABLED=True)
def test_public_workspace_docs_show_public_endpoints(client):
    workspace = Workspace.objects.create(name="Public APIs", slug="public-apis", visibility=Workspace.Visibility.PUBLIC)
    Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.REST,
        name="List invoices",
        slug="list-invoices",
        visibility=Endpoint.Visibility.PUBLIC,
    )
    Endpoint.objects.create(
        workspace=workspace,
        protocol=Endpoint.Protocol.REST,
        name="Internal metrics",
        slug="internal-metrics",
        visibility=Endpoint.Visibility.PRIVATE,
    )

    response = client.get(reverse("api_workspace:public_workspace_docs", args=[workspace.slug]))

    assert response.status_code == 200
    assert b"Public APIs" in response.content
    assert b"List invoices" in response.content
    assert b"Internal metrics" not in response.content
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_public_docs.py -q
```

Expected: FAIL because `public_workspace_docs` route does not exist.

- [ ] **Step 3: Implement public docs views and URLs**

Create `src/django_api_workspace/docs/__init__.py`:

```python
```

Create `src/django_api_workspace/docs/views.py`:

```python
from django.http import Http404
from django.views.generic import DetailView

from django_api_workspace import settings as package_settings
from django_api_workspace.models import Endpoint, Workspace


class PublicWorkspaceDocsView(DetailView):
    model = Workspace
    slug_field = "slug"
    slug_url_kwarg = "workspace_slug"
    template_name = "django_api_workspace/docs/workspace_public.html"

    def get_object(self, queryset=None):
        workspace = super().get_object(queryset)
        if not package_settings.public_docs_enabled():
            raise Http404("Public docs are disabled")
        if workspace.visibility != Workspace.Visibility.PUBLIC:
            raise Http404("Workspace docs are not public")
        return workspace

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["public_endpoints"] = self.object.endpoints.filter(
            visibility=Endpoint.Visibility.PUBLIC,
            archived_at__isnull=True,
        ).order_by("name")
        return context
```

Create `src/django_api_workspace/docs/urls.py`:

```python
from django.urls import path

from django_api_workspace.docs.views import PublicWorkspaceDocsView

urlpatterns = [
    path("<slug:workspace_slug>/", PublicWorkspaceDocsView.as_view(), name="public_workspace_docs"),
]
```

- [ ] **Step 4: Implement public docs template**

Create `src/django_api_workspace/templates/django_api_workspace/docs/workspace_public.html`:

```html
{% extends "django_api_workspace/base.html" %}

{% block title %}{{ object.name }} API Docs{% endblock %}

{% block content %}
  <h1>{{ object.name }} API Docs</h1>
  {% if object.description %}
    <p>{{ object.description }}</p>
  {% endif %}

  {% if public_endpoints %}
    <ul>
      {% for endpoint in public_endpoints %}
        <li>
          <strong>{{ endpoint.get_protocol_display }}</strong>
          {{ endpoint.name }}
          {% if endpoint.summary %}<span>{{ endpoint.summary }}</span>{% endif %}
        </li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No public endpoints are published.</p>
  {% endif %}
{% endblock %}
```

- [ ] **Step 5: Run public docs tests**

Run:

```bash
python -m pytest tests/test_public_docs.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/django_api_workspace/docs src/django_api_workspace/templates/django_api_workspace/docs tests/test_public_docs.py
git commit -m "feat: add private-by-default public docs"
```

---

### Task 9: Bootstrap Management Command

**Files:**
- Create: `src/django_api_workspace/management/__init__.py`
- Create: `src/django_api_workspace/management/commands/__init__.py`
- Create: `src/django_api_workspace/management/commands/apiworkspace.py`
- Create: `tests/test_management_commands.py`

- [ ] **Step 1: Write failing management command tests**

Create `tests/test_management_commands.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from django_api_workspace.models import Workspace, WorkspaceMember


@pytest.mark.django_db
def test_bootstrap_command_creates_workspace_without_owner():
    call_command("apiworkspace", "bootstrap", "--workspace", "Demo APIs")

    workspace = Workspace.objects.get(slug="demo-apis")
    assert workspace.name == "Demo APIs"
    assert workspace.memberships.count() == 0


@pytest.mark.django_db
def test_bootstrap_command_assigns_owner_when_username_is_given():
    user = get_user_model().objects.create_user(username="admin", password="pass")

    call_command("apiworkspace", "bootstrap", "--workspace", "Admin APIs", "--owner", "admin")

    workspace = Workspace.objects.get(slug="admin-apis")
    assert workspace.memberships.get(user=user).role == WorkspaceMember.Role.OWNER
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
python -m pytest tests/test_management_commands.py -q
```

Expected: FAIL with `Unknown command: 'apiworkspace'`.

- [ ] **Step 3: Implement the management command**

Create `src/django_api_workspace/management/__init__.py`:

```python
```

Create `src/django_api_workspace/management/commands/__init__.py`:

```python
```

Create `src/django_api_workspace/management/commands/apiworkspace.py`:

```python
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from django_api_workspace.models import Workspace, WorkspaceMember


class Command(BaseCommand):
    help = "Manage Django API Workspace."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["bootstrap"])
        parser.add_argument("--workspace", default="Default API Workspace")
        parser.add_argument("--owner", default="")

    def handle(self, *args, **options):
        if options["action"] == "bootstrap":
            self._bootstrap(options)

    def _bootstrap(self, options):
        workspace_name = options["workspace"]
        workspace, created = Workspace.objects.get_or_create(
            slug=slugify(workspace_name),
            defaults={"name": workspace_name},
        )

        owner_username = options["owner"]
        if owner_username:
            try:
                owner = get_user_model().objects.get(username=owner_username)
            except get_user_model().DoesNotExist as exc:
                raise CommandError(f"Owner user '{owner_username}' does not exist") from exc
            WorkspaceMember.objects.get_or_create(
                workspace=workspace,
                user=owner,
                defaults={"role": WorkspaceMember.Role.OWNER},
            )

        state = "created" if created else "exists"
        self.stdout.write(self.style.SUCCESS(f"Workspace '{workspace.name}' {state}."))
```

- [ ] **Step 4: Run management command tests**

Run:

```bash
python -m pytest tests/test_management_commands.py -q
```

Expected: PASS with `2 passed`.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/django_api_workspace/management tests/test_management_commands.py
git commit -m "feat: add api workspace bootstrap command"
```

---

### Task 10: Final Foundation Verification

**Files:**
- Modify only if verification finds a concrete defect in files introduced by earlier tasks.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Check migrations are current**

Run:

```bash
python -m django makemigrations django_api_workspace --settings=tests.settings --check --dry-run
```

Expected: command exits successfully and reports no model changes.

- [ ] **Step 3: Run Django system checks**

Run:

```bash
python -m django check --settings=tests.settings
```

Expected: `System check identified no issues`.

- [ ] **Step 4: Check whitespace**

Run:

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 5: Inspect final status**

Run:

```bash
git status --short
```

Expected: no uncommitted changes.

If files remain modified because a verification fix was needed, commit them:

```bash
git add src tests pyproject.toml README.md .gitignore
git commit -m "fix: stabilize api workspace foundation"
```

---

## Self-Review

Spec coverage for this foundation slice:

- New project package: covered by Task 1.
- Django embedded install model: covered by Task 1.
- User login/register dashboard: covered by Task 6.
- User-created workspaces: covered by Tasks 5 and 7.
- Workspace roles and permissions: covered by Tasks 2 and 5.
- Collections and API groups: covered by Tasks 3 and 7.
- Endpoint documentation model: covered by Task 3.
- REST, GraphQL, WebSocket, and gRPC model support: covered by Task 3.
- Examples: covered by Task 3.
- Environments, variables, auth profiles, request history, saved responses, assertions, jobs, and audit: covered by Task 4.
- Dashboard-first setup and CRUD foundation: covered by Tasks 6 and 7.
- Private-by-default public docs: covered by Task 8.
- Optional CLI bootstrap mirror: covered by Task 9.
- Verification: covered by Task 10.

Requirements intentionally assigned to follow-up plans:

- OpenAPI, GraphQL, proto, and WebSocket importers.
- Django/DRF/GraphQL/Channels/gRPC discovery scanning.
- REST, GraphQL, WebSocket, and gRPC request execution adapters.
- Visual assertion builder beyond model foundation.
- Static docs export and token-protected docs.
- Production dashboard styling and advanced workflows.

No unresolved placeholders remain in this plan.
