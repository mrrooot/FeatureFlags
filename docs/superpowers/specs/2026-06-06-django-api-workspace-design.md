# Django API Workspace Design

## Purpose

Build a new installable Django package named `django-api-workspace` that gives a host Django application a full embedded API documentation, collaboration, and testing workspace.

The package combines the strongest parts of Swagger and Postman:

- rich API documentation
- importable/generated API references
- collections and grouped APIs
- runnable requests
- environments and variables
- examples and saved responses
- tests and assertions
- public/private developer documentation

The package should install and behave like the existing feature flags package model: a Django project adds the app to `INSTALLED_APPS`, mounts package URLs, runs migrations, and gets a built-in dashboard.

## Product Scope

The package includes all major protocol families from the beginning:

- REST and OpenAPI
- GraphQL
- WebSocket
- gRPC

It includes both internal workspace features and published documentation features:

- user login, registration, password reset, and authenticated dashboard access
- user-created workspaces
- workspace membership and roles
- collections and nested API groups
- endpoint-level documentation
- long-form documentation pages
- request, response, message, schema, and flow examples
- protocol-aware request runner
- environments and variables
- auth profiles
- secret masking
- request history
- saved responses
- visual test/assertion builder
- public/private docs controls
- token-protected docs
- static documentation export
- OpenAPI import/export
- GraphQL schema/introspection import
- `.proto` import
- WebSocket definition import
- Django/DRF/GraphQL/Channels/gRPC host discovery
- dashboard-first import, export, discovery, publish, and security tools
- optional management commands for automation and CI

Normal users should be able to perform important product workflows from the dashboard. Management commands exist as automation mirrors, not as the primary user experience.

## Non-Goals

The package will not be a separate SaaS service. It will not require a separate control-plane server for the primary use case. It will not require Node.js for the dashboard. It will not publish secrets, private environment values, request history, or internal-only examples by default.

The package may support future integrations with external auth, team billing, hosted sync, or advanced scripting runtimes, but those are not required for the initial design.

## Installation Model

Expected host app setup:

```python
INSTALLED_APPS = [
    # ...
    "django_api_workspace",
]
```

```python
from django.urls import include, path

urlpatterns = [
    # ...
    path("api-workspace/", include("django_api_workspace.urls")),
]
```

Expected setup commands:

```bash
python manage.py migrate
python manage.py apiworkspace bootstrap
```

The package uses the host application's Django database and Django auth system. It provides dashboard account views for login, registration, password reset, and workspace access when the host app wants a self-contained experience.

Package settings examples:

```python
API_WORKSPACE_ALLOW_SIGNUP = True
API_WORKSPACE_INVITE_ONLY = False
API_WORKSPACE_PUBLIC_DOCS_ENABLED = False
API_WORKSPACE_RUNNER_ENABLED = True
API_WORKSPACE_ALLOWED_OUTBOUND_HOSTS = []
API_WORKSPACE_SECRET_STORAGE = "masked"
```

## Architecture

The package is one embedded Django app with modular internals.

Main package modules:

- `accounts`: login, registration, password reset integration, user dashboard entry points
- `core`: workspaces, members, collections, groups, endpoints, shared domain services
- `docs`: documentation pages, examples, publishing metadata, public docs rendering
- `dashboard`: authenticated workspace UI, forms, views, templates, static assets
- `runner`: shared runner orchestration, request execution, response capture, variable resolution
- `environments`: environments, variables, secret handling
- `auth_profiles`: reusable auth configuration for requests
- `tests`: assertions, test suites, test runs, result snapshots
- `history`: request history, saved responses, retention policies
- `importers`: OpenAPI, GraphQL, proto, WebSocket definition import jobs
- `exporters`: static docs, OpenAPI, GraphQL, proto/reference, JSON project export
- `discovery`: Django/DRF/GraphQL/Channels/gRPC host project scanning
- `audit`: workspace, docs, endpoint, environment, import, export, publish, and member changes
- `management`: optional automation and CI commands
- `protocols.rest`: REST/OpenAPI models, import/export mapping, HTTP runner adapter
- `protocols.graphql`: GraphQL schema references, operation mapping, GraphQL runner adapter
- `protocols.websocket`: WebSocket connection/message models and runner adapter
- `protocols.grpc`: proto/service/method models and gRPC runner adapter

The core rule is: shared workspace features are protocol-agnostic, while protocol behavior is isolated behind adapters.

Dashboard, public docs, static export, and CLI commands should all use service-layer APIs rather than duplicating behavior in views or commands.

## Account And Workspace Model

The dashboard is account-based, not only staff-only.

Users can:

- register or log in
- create personal or team workspaces
- switch between owned and joined workspaces
- invite members
- manage roles according to permissions

Workspace roles:

- `Owner`: full control, including workspace deletion and ownership transfer
- `Admin`: manage members, settings, imports, publishing, and security controls
- `Editor`: create and edit docs, endpoints, examples, tests, and runnable requests
- `Viewer`: read private docs and examples; runner access is configurable

Access rules:

- anonymous users can only see public docs when enabled
- logged-in users see their own workspace dashboard
- workspace members see only workspace content they are allowed to access
- package-level staff administration can be enabled for host app administrators

## Data Model

Core models:

- `Workspace`: top-level API workspace
- `WorkspaceMember`: user, workspace, role, status
- `WorkspaceInvitation`: email/user invitation, role, token, expiry, accepted state
- `Collection`: Postman-like collection inside a workspace
- `ApiGroup`: nested group/folder inside a collection
- `Endpoint`: one documented operation with a protocol type
- `DocumentationPage`: long-form docs attached to workspace, collection, group, or endpoint
- `Example`: request, response, message, schema, or flow example
- `Environment`: local, development, staging, production, or custom environment
- `Variable`: environment-scoped variables, with secret masking support
- `AuthProfile`: reusable authentication configuration
- `RequestTemplate`: saved runnable request attached to an endpoint or collection
- `RequestHistory`: executed request record
- `SavedResponse`: named response snapshot
- `Assertion`: reusable test expectation
- `TestSuite`: grouped assertions and request templates
- `TestRun`: execution result for endpoint, collection, or workspace tests
- `ImportJob`: import source, status, logs, errors, and created/updated objects
- `ExportJob`: export target, status, logs, errors, and output metadata
- `DiscoverySnapshot`: detected host routes/services and changes
- `AuditLog`: who changed what, before/after payloads, reason, timestamp

Protocol-specific detail models:

- `RestOperation`: method, path, query params, headers, body schema, response schemas
- `GraphQLOperation`: query, mutation, subscription, operation name, variables, schema reference
- `WebSocketOperation`: URL, handshake headers, message event types, send/receive examples
- `GrpcOperation`: package, service, method, streaming mode, request/response schema, metadata

Everything user-facing is anchored by `Endpoint`, while each endpoint delegates protocol-specific behavior to its detail model.

## Dashboard UX

The dashboard should feel like a serious API command center: dense, clear, professional, and useful for repeated work.

Main areas:

- personal dashboard: owned and joined workspaces
- workspace overview: API health, recent changes, failed imports, recent requests, public docs status
- collections: tree of collections, groups, and endpoints
- endpoint detail: docs, schema, examples, runner, tests, history, settings
- runner: protocol-specific request composer and response viewer
- examples: request, response, message, schema, and flow examples
- environments: variables, secrets, base URLs, and defaults
- auth profiles: bearer, basic, API key, OAuth-ready profiles, custom headers, gRPC metadata
- imports and discovery: upload/import, scan host app, review changes, apply selected items
- public docs: preview, visibility, token access, publishing, static export
- history: request logs, saved responses, replay actions, retention controls
- members: invitations, roles, access review
- settings: workspace settings, runner controls, security check, export behavior

Endpoint detail tabs:

```text
Docs | Schema | Examples | Runner | Tests | History | Settings
```

The key workflow is that a user can document, test, save examples, and publish from the same endpoint screen.

## Dashboard-First Features

All important product features must be available in the dashboard:

- setup wizard and first workspace creation
- OpenAPI import
- GraphQL schema import
- `.proto` import
- WebSocket definition import
- Django/DRF/GraphQL/Channels/gRPC discovery
- review discovered APIs before saving
- export static docs
- export OpenAPI
- publish/unpublish public docs
- rotate public docs tokens
- manage environments and secrets
- manage request history retention
- run security checks
- view import/export logs
- run endpoint, collection, or workspace tests

Management commands mirror important workflows for automation and CI, but the dashboard is the primary product surface.

## Import And Discovery

The package supports four creation paths.

Manual creation:

- users create collections, groups, endpoints, docs, examples, request templates, and tests directly in the dashboard

REST/OpenAPI:

- import OpenAPI JSON or YAML
- create REST endpoints, schemas, examples, tags/groups, descriptions, and response documentation
- export REST endpoint docs back to OpenAPI

Protocol imports:

- import GraphQL schema or introspection JSON
- import `.proto` files for gRPC services and methods
- import WebSocket event/message definitions from JSON/YAML package format

Django host discovery:

- scan Django URL patterns
- inspect DRF APIViews, ViewSets, routers, serializers, and permissions where possible
- inspect configured GraphQL schema where available
- inspect Channels/WebSocket routes where available
- inspect registered gRPC services where the host exposes a compatible registry

Discovery is review-based. It creates a `DiscoverySnapshot`, displays added, changed, and removed APIs, and lets users approve selected changes before mutating workspace content.

## Runner And Testing

Shared runner features:

- select workspace, environment, and auth profile
- resolve variables such as `{{base_url}}`, `{{token}}`, and `{{user_id}}`
- send requests from endpoint templates or ad hoc runner tabs
- save requests into collections
- save responses as examples
- store request history
- display status, timing, headers, body, errors, and logs
- compare responses against saved examples
- run assertions/tests

Protocol runners:

- REST: method, URL/path, query params, headers, body, multipart, cookies
- GraphQL: endpoint URL, query/mutation/subscription, operation name, variables, headers
- WebSocket: connect, disconnect, send messages, receive event stream, save message examples
- gRPC: host, service, method, metadata, request message, unary/server streaming/client streaming/bidirectional streaming where possible

Assertions:

- REST: status, header, JSON path, schema, body text, response time
- GraphQL: errors array, data path, schema shape, response time
- WebSocket: expected event received, message schema, sequence order, timeout
- gRPC: status code, metadata, message field path, streaming sequence, response time

Dashboard testing features:

- create request tests from runner responses
- add assertions visually
- group tests by collection and environment
- run one endpoint test
- run a whole collection
- run workspace test suites
- view pass/fail history
- save test result snapshots
- compare current responses with saved examples
- mark examples as contract examples

Automation support:

- run workspace tests in CI through a management command
- export JSON or JUnit-style test results
- choose environment for CI runs
- fail CI when assertions fail

## Public Docs And Export

Public docs are separate from private editing.

Public docs modes:

- private only
- public hosted docs
- token-protected docs
- static export

Publish controls:

- owners/admins decide what is public
- collections and endpoints can be private, internal, token-protected, or public
- examples can be publishable or internal-only
- secrets, private environment values, request history, saved responses, and private notes never publish by default
- public docs read from the same workspace source content as the dashboard

Export formats:

- static HTML/CSS/JS documentation site
- OpenAPI export for REST
- GraphQL SDL export where possible
- gRPC/proto reference packaging
- JSON project export/import for backup and migration

The public docs should feel like a polished developer portal: guides, grouped endpoints, examples, auth instructions, schemas, and optional try-it controls.

## Security And Permissions

Default security posture:

- dashboard requires login
- public docs are disabled
- runner is only available to authenticated workspace users
- secrets are masked
- secrets never publish
- self-signup can be enabled, disabled, or invite-only

Security controls:

- per-workspace visibility
- per-collection and endpoint publish visibility
- role-based permissions
- secret masking in UI
- secret exclusion from exports/public docs by default
- optional encrypted secret storage in a future version
- outbound request allowlist/blocklist
- package setting to disable runner in production
- audit logs for workspace, endpoint, docs, environment, import, export, publish, request template, and member changes
- request history retention settings
- CSRF protection for dashboard actions
- rate limiting hooks for public docs and shared tokens

Runner safety:

- admins can restrict outbound hosts
- package settings can disable request execution
- request history can be pruned
- static exports omit runtime-only and secret fields unless explicitly allowed by privileged users

## Management Commands

Management commands are optional automation helpers.

Commands:

- `apiworkspace bootstrap`: create default package settings and optionally a first workspace/admin membership
- `apiworkspace discover`: run host app discovery and create a discovery snapshot
- `apiworkspace import-openapi`: import OpenAPI JSON/YAML
- `apiworkspace import-graphql`: import GraphQL schema/introspection
- `apiworkspace import-proto`: import gRPC proto files
- `apiworkspace export-docs`: export static docs
- `apiworkspace export-openapi`: export REST endpoints to OpenAPI
- `apiworkspace run-tests`: run endpoint, collection, or workspace tests for CI
- `apiworkspace rotate-token`: rotate public docs or shared access tokens
- `apiworkspace prune-history`: delete old request history
- `apiworkspace check-security`: report unsafe configuration

Commands call the same service layer as the dashboard.

## Error Handling

Import errors:

- imports should be transactional where practical
- partial failures are recorded on `ImportJob`
- invalid specs show line/path-aware messages when available
- imports can be previewed before applying changes

Discovery errors:

- unsupported views/routes are recorded as warnings
- discovery never mutates endpoint docs until a user approves changes
- removed APIs are marked as candidates for archive, not deleted automatically

Runner errors:

- connection failures, timeouts, DNS errors, TLS errors, protocol errors, and assertion failures are shown distinctly
- secrets are redacted from logs and error messages
- outbound host restrictions return clear dashboard errors

Publishing/export errors:

- export jobs keep logs and downloadable failure details
- public docs publishing validates visibility and secret leakage rules before publishing

## Testing Strategy

Package tests should cover:

- model and migration behavior
- workspace membership and permissions
- account registration/login flows
- dashboard access controls
- public docs visibility rules
- secret masking and export safety
- importers for OpenAPI, GraphQL, proto, and WebSocket definitions
- host discovery snapshots
- runner adapters for REST, GraphQL, WebSocket, and gRPC
- variable resolution
- auth profile application
- request history and retention
- saved responses and examples
- assertions and test suites
- static docs export
- management commands
- audit logs

Tests should use SQLite for core compatibility. Protocol runner tests can use local fake servers or mocked transport adapters so the suite stays reliable.

## First Implementation Shape

Even though all protocols are in scope from the beginning, the implementation should keep strong boundaries:

1. package foundation, accounts, workspaces, roles, and dashboard shell
2. shared collections, groups, endpoints, docs, examples, environments, auth profiles
3. protocol detail models for REST, GraphQL, WebSocket, and gRPC
4. dashboard CRUD for all core objects
5. import/discovery job framework
6. runner orchestration and protocol adapters
7. history, saved responses, and assertions
8. public docs and static export
9. optional management command mirrors

The user-facing product should show all protocol families from the beginning. Internally, adapters can evolve independently as long as each protocol has documentation, examples, import/discovery path, runner behavior, and test support.

## Resolved Decisions

- Project type: new package, separate from the feature flags package
- Framework: installable Django app package
- Product model: embedded dashboard inside host Django apps
- Access model: user accounts, self-created workspaces, membership roles
- Main product surface: dashboard-first
- CLI role: optional automation/CI helper
- Protocol scope: REST, GraphQL, WebSocket, and gRPC from day one
- Documentation model: rich docs plus examples at workspace, collection, group, and endpoint levels
- Runner scope: Postman-like runner for all protocol families
- Import scope: OpenAPI, GraphQL schema/introspection, proto, WebSocket definitions
- Discovery scope: Django, DRF, configured GraphQL, Channels/WebSocket, compatible gRPC registrations
- Publishing: private by default, optional public/token-protected/static docs
- Security posture: login required, secrets masked, public docs disabled by default
