# LaunchDarkly-Style Targeting Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dashboard-first LaunchDarkly-style Targeting tab that persists per-environment targeting documents and drives the real evaluator.

**Architecture:** Add `FlagState.targeting` as the per-environment targeting document, then route all normalization, validation, matching, and rollout behavior through focused targeting modules. Keep the dashboard server-rendered Django with a small static JavaScript helper for add/remove form rows; local and remote evaluation continue to call the same evaluator.

**Tech Stack:** Django ORM and migrations, Django forms/views/templates, plain CSS, plain JavaScript, pytest, pytest-django, SQLite-compatible JSONField behavior.

---

## Runtime Note

Use the local test command already used by this workspace. For example:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_evaluator.py -q
```

If the virtual environment is active in a POSIX shell, the equivalent command is:

```bash
python -m pytest tests/test_evaluator.py -q
```

---

## File Structure

- Modify `src/django_feature_flags/models/core.py`: add `FlagState.targeting`.
- Create `src/django_feature_flags/migrations/0002_flagstate_targeting.py`: add the targeting JSON field.
- Create `src/django_feature_flags/targeting/documents.py`: normalize and validate targeting documents.
- Modify `src/django_feature_flags/targeting/operators.py`: add multi-context attribute and clause matching.
- Modify `src/django_feature_flags/targeting/rollout.py`: add weighted rollout variation selection.
- Modify `src/django_feature_flags/evaluation/evaluator.py`: evaluate the targeting document and return richer reason detail.
- Create `src/django_feature_flags/dashboard/targeting_forms.py`: parse dashboard targeting submissions into targeting documents.
- Modify `src/django_feature_flags/dashboard/views.py`: add flag detail, targeting save, and preview workflows.
- Modify `src/django_feature_flags/dashboard/urls.py`: add flag detail and preview routes.
- Modify `src/django_feature_flags/templates/django_feature_flags/flag_list.html`: point Edit flag to the new detail page.
- Create `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`: render the single LaunchDarkly-style Targeting tab.
- Modify `src/django_feature_flags/static/django_feature_flags/dashboard.css`: add Targeting tab layout styles.
- Create `src/django_feature_flags/static/django_feature_flags/targeting.js`: add/remove targeting form rows.
- Modify `pyproject.toml`: include `static/django_feature_flags/*.js` in package data.
- Create `tests/test_targeting_documents.py`: service, validation, and compatibility tests.
- Modify `tests/test_targeting.py`: multi-context matching and weighted rollout tests.
- Modify `tests/test_evaluator.py`: targeting document evaluation tests.
- Modify `tests/test_dashboard.py`: flag detail rendering and route tests.
- Modify `tests/test_dashboard_workflows.py`: save, preview, audit, and approval workflow tests.

---

### Task 1: Add `FlagState.targeting` Persistence

**Files:**
- Modify: `src/django_feature_flags/models/core.py`
- Create: `src/django_feature_flags/migrations/0002_flagstate_targeting.py`
- Create: `tests/test_targeting_documents.py`

- [ ] **Step 1: Write the failing model default test**

Create `tests/test_targeting_documents.py`:

```python
import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation


@pytest.fixture
def boolean_flag_stack():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="new_checkout", name="New Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", name="Off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", name="On", value=True)
    state = FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    return project, environment, flag, state, off, on


@pytest.mark.django_db
def test_flag_state_targeting_defaults_to_empty_document(boolean_flag_stack):
    _, _, _, state, _, _ = boolean_flag_stack

    assert state.targeting == {}
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting_documents.py::test_flag_state_targeting_defaults_to_empty_document -q
```

Expected: FAIL with `AttributeError: 'FlagState' object has no attribute 'targeting'`.

- [ ] **Step 3: Add the model field**

In `src/django_feature_flags/models/core.py`, add this field to `FlagState` after `rollout`:

```python
    targeting = models.JSONField(default=dict, blank=True)
```

- [ ] **Step 4: Create the migration**

Run:

```powershell
.venv\Scripts\python.exe -m django makemigrations django_feature_flags
```

Expected: Django creates `src/django_feature_flags/migrations/0002_flagstate_targeting.py`.

The migration should contain an operation equivalent to:

```python
migrations.AddField(
    model_name="flagstate",
    name="targeting",
    field=models.JSONField(blank=True, default=dict),
)
```

- [ ] **Step 5: Run the model test and existing model tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting_documents.py::test_flag_state_targeting_defaults_to_empty_document tests\test_models.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/django_feature_flags/models/core.py src/django_feature_flags/migrations/0002_flagstate_targeting.py tests/test_targeting_documents.py
git commit -m "feat(targeting): add per-environment targeting document"
```

---

### Task 2: Add Targeting Document Normalization And Validation

**Files:**
- Create: `src/django_feature_flags/targeting/documents.py`
- Modify: `tests/test_targeting_documents.py`

- [ ] **Step 1: Add failing normalization and validation tests**

Append to `tests/test_targeting_documents.py`:

```python
from django_feature_flags.targeting.documents import (
    ROLLOUT_SCALE,
    TargetingValidationError,
    normalized_targeting,
    validate_targeting,
)


@pytest.mark.django_db
def test_normalized_targeting_derives_legacy_default_and_rollout(boolean_flag_stack):
    _, environment, flag, state, off, on = boolean_flag_stack
    state.enabled = True
    state.rollout = {"percentage": 25, "variation_key": on.key}
    state.save(update_fields=["enabled", "rollout"])

    document = normalized_targeting(state)

    assert document["off_variation"] == off.key
    assert document["fallthrough"]["rollout"]["context_kind"] == "user"
    assert document["fallthrough"]["rollout"]["variations"] == [
        {"variation_key": on.key, "weight": 25000},
        {"variation_key": off.key, "weight": 75000},
    ]


@pytest.mark.django_db
def test_validate_targeting_accepts_known_variations_and_segments(boolean_flag_stack):
    project, environment, flag, _, _, on = boolean_flag_stack
    project.segments.create(key="beta_users", name="Beta Users")
    document = {
        "off_variation": "off",
        "prerequisites": [],
        "targets": [{"context_kind": "user", "variation_key": on.key, "values": ["user-1"]}],
        "rules": [
            {
                "id": "rule-1",
                "description": "Beta users",
                "clauses": [
                    {
                        "context_kind": "user",
                        "attribute": "segment",
                        "operator": "segment_match",
                        "values": ["beta_users"],
                        "negate": False,
                    }
                ],
                "serve": {"variation_key": on.key},
            }
        ],
        "fallthrough": {"variation_key": "off"},
        "track_events": False,
    }

    cleaned = validate_targeting(flag, environment, document)

    assert cleaned["rules"][0]["id"] == "rule-1"
    assert cleaned["targets"][0]["values"] == ["user-1"]


@pytest.mark.django_db
def test_validate_targeting_rejects_missing_variation(boolean_flag_stack):
    _, environment, flag, _, _, _ = boolean_flag_stack
    document = {"off_variation": "missing", "prerequisites": [], "targets": [], "rules": [], "fallthrough": {"variation_key": "missing"}}

    with pytest.raises(TargetingValidationError) as exc:
        validate_targeting(flag, environment, document)

    assert "off_variation" in exc.value.errors
    assert "fallthrough" in exc.value.errors


@pytest.mark.django_db
def test_validate_targeting_rejects_rollout_weights_that_do_not_total_scale(boolean_flag_stack):
    _, environment, flag, _, _, _ = boolean_flag_stack
    document = {
        "off_variation": "off",
        "prerequisites": [],
        "targets": [],
        "rules": [],
        "fallthrough": {
            "rollout": {
                "context_kind": "user",
                "variations": [
                    {"variation_key": "off", "weight": ROLLOUT_SCALE - 1},
                ],
            }
        },
    }

    with pytest.raises(TargetingValidationError) as exc:
        validate_targeting(flag, environment, document)

    assert exc.value.errors["fallthrough"] == ["Rollout weights must total 100000."]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting_documents.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'django_feature_flags.targeting.documents'`.

- [ ] **Step 3: Create `targeting/documents.py`**

Create `src/django_feature_flags/targeting/documents.py`:

```python
from copy import deepcopy

ROLLOUT_SCALE = 100000


class TargetingValidationError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Invalid targeting document.")


def empty_targeting(default_variation_key=""):
    return {
        "off_variation": default_variation_key,
        "prerequisites": [],
        "targets": [],
        "rules": [],
        "fallthrough": {"variation_key": default_variation_key} if default_variation_key else {},
        "track_events": False,
    }


def normalized_targeting(state):
    default_key = state.default_variation.key if state.default_variation else ""
    document = empty_targeting(default_key)
    document.update(deepcopy(state.targeting or {}))
    if "off_variation" not in document or not document["off_variation"]:
        document["off_variation"] = default_key
    if not document.get("fallthrough"):
        document["fallthrough"] = {"variation_key": default_key} if default_key else {}
    if state.rollout and state.rollout.get("variation_key") and state.rollout.get("percentage"):
        rollout_weight = int(float(state.rollout["percentage"]) * 1000)
        fallback_weight = ROLLOUT_SCALE - rollout_weight
        document["fallthrough"] = {
            "rollout": {
                "context_kind": "user",
                "salt": state.environment.key,
                "variations": [
                    {"variation_key": state.rollout["variation_key"], "weight": rollout_weight},
                    {"variation_key": default_key, "weight": fallback_weight},
                ],
            }
        }
    return document


def validate_targeting(flag, environment, document):
    errors = {}
    cleaned = empty_targeting(flag.variations.filter(is_default=True).values_list("key", flat=True).first() or "")
    cleaned.update(deepcopy(document or {}))
    variation_keys = set(flag.variations.values_list("key", flat=True))
    segment_keys = set(flag.project.segments.values_list("key", flat=True))
    flag_keys = set(flag.project.flags.exclude(pk=flag.pk).values_list("key", flat=True))

    _validate_variation_key(errors, "off_variation", cleaned.get("off_variation"), variation_keys)
    _validate_prerequisites(errors, cleaned.get("prerequisites", []), flag_keys)
    _validate_targets(errors, cleaned.get("targets", []), variation_keys)
    _validate_rules(errors, cleaned.get("rules", []), variation_keys, segment_keys)
    _validate_serve(errors, "fallthrough", cleaned.get("fallthrough", {}), variation_keys)

    if errors:
        raise TargetingValidationError(errors)
    cleaned["prerequisites"] = cleaned.get("prerequisites", [])
    cleaned["targets"] = cleaned.get("targets", [])
    cleaned["rules"] = cleaned.get("rules", [])
    cleaned["track_events"] = bool(cleaned.get("track_events", False))
    return cleaned


def _validate_variation_key(errors, section, variation_key, variation_keys):
    if variation_key and variation_key not in variation_keys:
        errors.setdefault(section, []).append(f"Variation '{variation_key}' does not exist.")


def _validate_prerequisites(errors, prerequisites, flag_keys):
    seen = set()
    for item in prerequisites:
        flag_key = str(item.get("flag_key", "")).strip()
        variation_key = str(item.get("variation_key", "")).strip()
        if not flag_key or flag_key not in flag_keys:
            errors.setdefault("prerequisites", []).append(f"Prerequisite flag '{flag_key or '<missing>'}' does not exist.")
        if not variation_key:
            errors.setdefault("prerequisites", []).append("Prerequisite variation is required.")
        if flag_key in seen:
            errors.setdefault("prerequisites", []).append(f"Prerequisite flag '{flag_key}' is duplicated.")
        seen.add(flag_key)


def _validate_targets(errors, targets, variation_keys):
    for item in targets:
        _validate_variation_key(errors, "targets", item.get("variation_key"), variation_keys)
        values = [str(value).strip() for value in item.get("values", []) if str(value).strip()]
        if not item.get("context_kind"):
            errors.setdefault("targets", []).append("Target context kind is required.")
        if not values:
            errors.setdefault("targets", []).append("Target values are required.")
        item["values"] = values


def _validate_rules(errors, rules, variation_keys, segment_keys):
    for rule in rules:
        if not rule.get("clauses"):
            errors.setdefault("rules", []).append("Each rule must have at least one clause.")
        for clause in rule.get("clauses", []):
            _validate_clause(errors, clause, segment_keys)
        _validate_serve(errors, "rules", rule.get("serve", {}), variation_keys)


def _validate_clause(errors, clause, segment_keys):
    for field in ("context_kind", "attribute", "operator"):
        if not clause.get(field):
            errors.setdefault("rules", []).append(f"Clause {field} is required.")
    values = clause.get("values", [])
    if clause.get("operator") == "segment_match":
        missing = [value for value in values if value not in segment_keys]
        for value in missing:
            errors.setdefault("rules", []).append(f"Segment '{value}' does not exist.")
    elif values in (None, []):
        errors.setdefault("rules", []).append("Clause values are required.")


def _validate_serve(errors, section, serve, variation_keys):
    if not serve:
        errors.setdefault(section, []).append("Serve behavior is required.")
        return
    if serve.get("variation_key"):
        _validate_variation_key(errors, section, serve["variation_key"], variation_keys)
        return
    rollout = serve.get("rollout")
    if not rollout:
        errors.setdefault(section, []).append("Serve behavior must choose a variation or rollout.")
        return
    variations = rollout.get("variations", [])
    total = sum(int(item.get("weight", 0)) for item in variations)
    if total != ROLLOUT_SCALE:
        errors.setdefault(section, []).append("Rollout weights must total 100000.")
    for item in variations:
        _validate_variation_key(errors, section, item.get("variation_key"), variation_keys)
```

- [ ] **Step 4: Run targeting document tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting_documents.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/django_feature_flags/targeting/documents.py tests/test_targeting_documents.py
git commit -m "feat(targeting): validate targeting documents"
```

---

### Task 3: Add Multi-Context Matching And Weighted Rollout Selection

**Files:**
- Modify: `src/django_feature_flags/targeting/operators.py`
- Modify: `src/django_feature_flags/targeting/rollout.py`
- Modify: `tests/test_targeting.py`

- [ ] **Step 1: Add failing multi-context and rollout tests**

Append to `tests/test_targeting.py`:

```python
from django_feature_flags.targeting.operators import clause_matches, normalize_contexts
from django_feature_flags.targeting.rollout import choose_weighted_variation


def test_normalize_contexts_treats_flat_context_as_user():
    contexts = normalize_contexts({"key": "user-123", "plan": "pro"})

    assert contexts == {"user": {"key": "user-123", "plan": "pro"}}


def test_clause_matches_nested_context_kind_attribute():
    context = {
        "user": {"key": "user-123", "plan": "pro"},
        "device": {"key": "phone-1", "platform": "ios"},
    }
    clause = {
        "context_kind": "device",
        "attribute": "platform",
        "operator": "in",
        "values": ["ios", "android"],
        "negate": False,
    }

    assert clause_matches(context, clause) is True


def test_clause_negate_inverts_result():
    context = {"organization": {"key": "org-1", "tier": "free"}}
    clause = {
        "context_kind": "organization",
        "attribute": "tier",
        "operator": "equals",
        "values": ["enterprise"],
        "negate": True,
    }

    assert clause_matches(context, clause) is True


def test_choose_weighted_variation_is_stable_for_context_key():
    rollout = {
        "context_kind": "user",
        "salt": "production",
        "variations": [
            {"variation_key": "control", "weight": 100000},
            {"variation_key": "treatment", "weight": 0},
        ],
    }

    assert choose_weighted_variation("checkout", {"user": {"key": "user-123"}}, rollout) == "control"
```

- [ ] **Step 2: Run targeting tests and verify failures**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting.py -q
```

Expected: FAIL with import errors for `clause_matches`, `normalize_contexts`, and `choose_weighted_variation`.

- [ ] **Step 3: Extend `operators.py`**

Add these functions to `src/django_feature_flags/targeting/operators.py`:

```python
def normalize_contexts(context):
    if not isinstance(context, dict):
        return {"user": {"key": "anonymous"}}
    known_context = any(isinstance(value, dict) and "key" in value for value in context.values())
    if known_context:
        return context
    return {"user": context}


def get_context_attribute(context, context_kind, attribute):
    contexts = normalize_contexts(context)
    selected = contexts.get(context_kind, {})
    if attribute == "key":
        return selected.get("key")
    return get_attribute(selected, attribute)


def clause_matches(context, clause):
    actual = get_context_attribute(context, clause["context_kind"], clause["attribute"])
    values = clause.get("values", [])
    expected = values if clause["operator"] in {"in", "not_in"} else (values[0] if values else clause.get("value"))
    matched = compare(actual, clause["operator"], expected)
    if clause.get("negate", False):
        return not matched
    return matched


def clauses_match(context, clauses):
    return all(clause_matches(context, clause) for clause in clauses)
```

Update `compare` so `in` and `not_in` handle missing or scalar expected values safely:

```python
    if operator == "in":
        return actual in (expected or [])
    if operator == "not_in":
        return actual not in (expected or [])
```

- [ ] **Step 4: Extend `rollout.py`**

Add this function to `src/django_feature_flags/targeting/rollout.py`:

```python
def choose_weighted_variation(flag_key, context, rollout):
    from django_feature_flags.targeting.operators import get_context_attribute

    context_kind = rollout.get("context_kind", "user")
    key = str(get_context_attribute(context, context_kind, "key") or "anonymous")
    bucket = bucket_context(flag_key, key, salt=rollout.get("salt", ""))
    running = 0
    for item in rollout.get("variations", []):
        running += int(item.get("weight", 0))
        if bucket < running:
            return item.get("variation_key", "")
    return ""
```

- [ ] **Step 5: Run targeting tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_targeting.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/django_feature_flags/targeting/operators.py src/django_feature_flags/targeting/rollout.py tests/test_targeting.py
git commit -m "feat(targeting): match multi-context clauses"
```

---

### Task 4: Evaluate Per-Environment Targeting Documents

**Files:**
- Modify: `src/django_feature_flags/evaluation/evaluator.py`
- Modify: `tests/test_evaluator.py`

- [ ] **Step 1: Add failing evaluator tests**

Append to `tests/test_evaluator.py`:

```python
@pytest.mark.django_db
def test_enabled_flag_uses_individual_multi_context_target(flag_setup):
    project, environment, flag, off, on = flag_setup
    state = flag.states.get(environment=environment)
    state.enabled = True
    state.targeting = {
        "off_variation": off.key,
        "targets": [{"context_kind": "organization", "variation_key": on.key, "values": ["org-9"]}],
        "rules": [],
        "fallthrough": {"variation_key": off.key},
    }
    state.save(update_fields=["enabled", "targeting"])

    result = evaluate(
        "new_checkout",
        {"user": {"key": "user-1"}, "organization": {"key": "org-9"}},
        default=False,
        project_key=project.key,
        environment_key=environment.key,
    )

    assert result.value is True
    assert result.variation_key == on.key
    assert result.reason == "target_match"
    assert result.detail["context_kind"] == "organization"


@pytest.mark.django_db
def test_enabled_flag_uses_rule_match_from_device_platform(flag_setup):
    project, environment, flag, off, on = flag_setup
    state = flag.states.get(environment=environment)
    state.enabled = True
    state.targeting = {
        "off_variation": off.key,
        "targets": [],
        "rules": [
            {
                "id": "ios-rule",
                "description": "iOS devices",
                "clauses": [
                    {
                        "context_kind": "device",
                        "attribute": "platform",
                        "operator": "in",
                        "values": ["ios"],
                        "negate": False,
                    }
                ],
                "serve": {"variation_key": on.key},
            }
        ],
        "fallthrough": {"variation_key": off.key},
    }
    state.save(update_fields=["enabled", "targeting"])

    result = evaluate(
        "new_checkout",
        {"user": {"key": "user-1"}, "device": {"key": "phone-1", "platform": "ios"}},
        default=False,
        project_key=project.key,
        environment_key=environment.key,
    )

    assert result.value is True
    assert result.reason == "rule_match"
    assert result.detail["rule_id"] == "ios-rule"


@pytest.mark.django_db
def test_disabled_flag_uses_off_variation_from_targeting(flag_setup):
    project, environment, flag, off, on = flag_setup
    state = flag.states.get(environment=environment)
    state.enabled = False
    state.targeting = {"off_variation": on.key, "fallthrough": {"variation_key": off.key}}
    state.save(update_fields=["enabled", "targeting"])

    result = evaluate("new_checkout", {"key": "user-1"}, default=False, project_key=project.key, environment_key=environment.key)

    assert result.value is True
    assert result.variation_key == on.key
    assert result.reason == "off"
```

- [ ] **Step 2: Run evaluator tests and verify failures**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_evaluator.py -q
```

Expected: FAIL because `EvaluationResult` has no `detail` field and evaluator ignores `FlagState.targeting`.

- [ ] **Step 3: Extend `EvaluationResult` and helper constructors**

In `src/django_feature_flags/evaluation/evaluator.py`, import `field`:

```python
from dataclasses import dataclass, field
```

Change `EvaluationResult`:

```python
@dataclass(frozen=True)
class EvaluationResult:
    value: object
    variation_key: str
    reason: str
    flag_key: str
    environment_key: str
    detail: dict = field(default_factory=dict)
```

Update result helpers to accept `detail=None` and store `detail or {}`.

- [ ] **Step 4: Add targeting document evaluation helpers**

In `evaluator.py`, add imports:

```python
from django_feature_flags.targeting.documents import TargetingValidationError, normalized_targeting, validate_targeting
from django_feature_flags.targeting.operators import clauses_match, normalize_contexts
from django_feature_flags.targeting.rollout import choose_weighted_variation
```

Add these helpers:

```python
def variation_by_key(flag, variation_key):
    if not variation_key:
        return None
    return flag.variations.filter(key=variation_key).first()


def serve_result(environment, flag, serve, context, reason, track, detail=None):
    variation_key = serve.get("variation_key", "")
    if not variation_key and serve.get("rollout"):
        variation_key = choose_weighted_variation(flag.key, context, serve["rollout"])
    variation = variation_by_key(flag, variation_key)
    if variation is None:
        return None
    return tracked_result(environment, flag, variation, context, reason, track, detail=detail or {})


def evaluate_targets(environment, flag, document, context, track):
    contexts = normalize_contexts(context)
    for target in document.get("targets", []):
        context_kind = target.get("context_kind", "user")
        key = str(contexts.get(context_kind, {}).get("key", ""))
        if key and key in target.get("values", []):
            return serve_result(
                environment,
                flag,
                {"variation_key": target.get("variation_key", "")},
                context,
                "target_match",
                track,
                detail={"context_kind": context_kind, "target_key": key},
            )
    return None


def evaluate_rules(environment, flag, document, context, track):
    for rule in document.get("rules", []):
        if clauses_match(context, rule.get("clauses", [])):
            result = serve_result(
                environment,
                flag,
                rule.get("serve", {}),
                context,
                "rule_match",
                track,
                detail={"rule_id": rule.get("id", "")},
            )
            if result is not None:
                return result
    return None
```

- [ ] **Step 5: Update evaluation order**

In `evaluate`, after emergency override and before legacy global `TargetingRule` evaluation:

```python
    document = normalized_targeting(state)
    try:
        document = validate_targeting(flag, environment, document)
    except TargetingValidationError as exc:
        return tracked_result(environment, flag, state.default_variation, context, "invalid_targeting", track, detail={"errors": exc.errors})

    if not state.enabled:
        variation = variation_by_key(flag, document.get("off_variation")) or state.default_variation
        return tracked_result(environment, flag, variation, context, "off", track)

    target_result = evaluate_targets(environment, flag, document, context, track)
    if target_result is not None:
        return target_result

    rule_result = evaluate_rules(environment, flag, document, context, track)
    if rule_result is not None:
        return rule_result

    fallthrough_result = serve_result(environment, flag, document.get("fallthrough", {}), context, "fallthrough", track)
    if fallthrough_result is not None:
        return fallthrough_result
```

Keep existing global `TargetingRule` evaluation only when `state.targeting` is empty.

- [ ] **Step 6: Update the existing disabled reason assertion**

In `tests/test_evaluator.py`, update:

```python
assert result.reason == "disabled"
```

to:

```python
assert result.reason == "off"
```

- [ ] **Step 7: Run evaluator tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_evaluator.py tests\test_targeting_documents.py tests\test_targeting.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/django_feature_flags/evaluation/evaluator.py tests/test_evaluator.py
git commit -m "feat(targeting): evaluate targeting documents"
```

---

### Task 5: Add Dashboard Targeting Form Parser

**Files:**
- Create: `src/django_feature_flags/dashboard/targeting_forms.py`
- Modify: `tests/test_dashboard_workflows.py`

- [ ] **Step 1: Add failing form parser tests**

Append to `tests/test_dashboard_workflows.py`:

```python
from django.http import QueryDict

from django_feature_flags.dashboard.targeting_forms import TargetingDocumentForm


@pytest.mark.django_db
def test_targeting_document_form_builds_targets_rules_and_fallthrough():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    data = QueryDict(mutable=True)
    data.update(
        {
            "enabled": "on",
            "off_variation": off.key,
            "target_context_kind_0": "user",
            "target_variation_key_0": on.key,
            "target_values_0": "user-1\nuser-2",
            "rule_id_0": "ios-rule",
            "rule_description_0": "iOS devices",
            "rule_serve_variation_key_0": on.key,
            "rule_clause_context_kind_0_0": "device",
            "rule_clause_attribute_0_0": "platform",
            "rule_clause_operator_0_0": "in",
            "rule_clause_values_0_0": "ios,android",
            "fallthrough_variation_key": off.key,
        }
    )
    data.setlist("target_index", ["0"])
    data.setlist("rule_index", ["0"])
    data.setlist("rule_clause_index_0", ["0"])

    form = TargetingDocumentForm(flag=flag, environment=environment, data=data)

    assert form.is_valid(), form.errors
    assert form.enabled is True
    assert form.cleaned_document["targets"][0]["values"] == ["user-1", "user-2"]
    assert form.cleaned_document["rules"][0]["clauses"][0]["values"] == ["ios", "android"]


@pytest.mark.django_db
def test_targeting_document_form_requires_change_reason_when_environment_requires_it():
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", require_change_reason=True)
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    data = QueryDict(mutable=True)
    data.update({"off_variation": off.key, "fallthrough_variation_key": off.key})

    form = TargetingDocumentForm(flag=flag, environment=environment, data=data)

    assert form.is_valid() is False
    assert form.errors["reason"] == ["Change reason is required for this environment."]
```

- [ ] **Step 2: Run parser tests and verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard_workflows.py::test_targeting_document_form_builds_targets_rules_and_fallthrough tests\test_dashboard_workflows.py::test_targeting_document_form_requires_change_reason_when_environment_requires_it -q
```

Expected: FAIL with import error for `django_feature_flags.dashboard.targeting_forms`.

- [ ] **Step 3: Create `dashboard/targeting_forms.py`**

Create `src/django_feature_flags/dashboard/targeting_forms.py`:

```python
from django import forms

from django_feature_flags.targeting.documents import TargetingValidationError, normalized_targeting, validate_targeting


class TargetingDocumentForm(forms.Form):
    reason = forms.CharField(required=False)

    def __init__(self, *, flag, environment, state=None, data=None):
        self.flag = flag
        self.environment = environment
        self.state = state
        self.cleaned_document = {}
        self.enabled = False
        super().__init__(data=data)

    def clean(self):
        cleaned = super().clean()
        if self.environment.require_change_reason and not (cleaned.get("reason") or "").strip():
            self.add_error("reason", "Change reason is required for this environment.")
        document = self._build_document()
        try:
            self.cleaned_document = validate_targeting(self.flag, self.environment, document)
        except TargetingValidationError as exc:
            for section, messages in exc.errors.items():
                self.add_error(None, f"{section}: {' '.join(messages)}")
        self.enabled = self.data.get("enabled") == "on"
        return cleaned

    def initial_document(self):
        if self.state is None:
            return {}
        return normalized_targeting(self.state)

    def _build_document(self):
        return {
            "off_variation": self.data.get("off_variation", ""),
            "prerequisites": self._build_prerequisites(),
            "targets": self._build_targets(),
            "rules": self._build_rules(),
            "fallthrough": self._build_fallthrough(),
            "track_events": self.data.get("track_events") == "on",
        }

    def _build_prerequisites(self):
        items = []
        for index in self.data.getlist("prerequisite_index"):
            flag_key = self.data.get(f"prerequisite_flag_key_{index}", "").strip()
            variation_key = self.data.get(f"prerequisite_variation_key_{index}", "").strip()
            if flag_key or variation_key:
                items.append({"flag_key": flag_key, "variation_key": variation_key})
        return items

    def _build_targets(self):
        items = []
        for index in self.data.getlist("target_index"):
            values = split_values(self.data.get(f"target_values_{index}", ""))
            if values:
                items.append(
                    {
                        "context_kind": self.data.get(f"target_context_kind_{index}", "user").strip() or "user",
                        "variation_key": self.data.get(f"target_variation_key_{index}", "").strip(),
                        "values": values,
                    }
                )
        return items

    def _build_rules(self):
        rules = []
        for index in self.data.getlist("rule_index"):
            clauses = []
            for clause_index in self.data.getlist(f"rule_clause_index_{index}"):
                values = split_values(self.data.get(f"rule_clause_values_{index}_{clause_index}", ""))
                clauses.append(
                    {
                        "context_kind": self.data.get(f"rule_clause_context_kind_{index}_{clause_index}", "user").strip() or "user",
                        "attribute": self.data.get(f"rule_clause_attribute_{index}_{clause_index}", "").strip(),
                        "operator": self.data.get(f"rule_clause_operator_{index}_{clause_index}", "equals").strip(),
                        "values": values,
                        "negate": self.data.get(f"rule_clause_negate_{index}_{clause_index}") == "on",
                    }
                )
            if clauses:
                rules.append(
                    {
                        "id": self.data.get(f"rule_id_{index}", f"rule-{index}").strip() or f"rule-{index}",
                        "description": self.data.get(f"rule_description_{index}", "").strip(),
                        "clauses": clauses,
                        "serve": {"variation_key": self.data.get(f"rule_serve_variation_key_{index}", "").strip()},
                    }
                )
        return rules

    def _build_fallthrough(self):
        variation_key = self.data.get("fallthrough_variation_key", "").strip()
        return {"variation_key": variation_key} if variation_key else {}


def split_values(raw_value):
    normalized = raw_value.replace(",", "\n")
    return [item.strip() for item in normalized.splitlines() if item.strip()]
```

- [ ] **Step 4: Run parser tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard_workflows.py::test_targeting_document_form_builds_targets_rules_and_fallthrough tests\test_dashboard_workflows.py::test_targeting_document_form_requires_change_reason_when_environment_requires_it -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/django_feature_flags/dashboard/targeting_forms.py tests/test_dashboard_workflows.py
git commit -m "feat(dashboard): parse targeting form submissions"
```

---

### Task 6: Add Flag Detail Routes, Save Workflow, Audit, And Approval Gate

**Files:**
- Modify: `src/django_feature_flags/dashboard/urls.py`
- Modify: `src/django_feature_flags/dashboard/views.py`
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_list.html`
- Modify: `tests/test_dashboard.py`
- Modify: `tests/test_dashboard_workflows.py`

- [ ] **Step 1: Add failing route and workflow tests**

Append to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_flag_list_edit_action_opens_flag_detail(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    flag = FeatureFlag.objects.create(project=project, key="recommendations", name="Recommendations", value_type="boolean")
    Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_list"))

    assert response.status_code == 200
    assert reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}) in response.content.decode()
```

Append to `tests/test_dashboard_workflows.py`:

```python
from django_feature_flags.models import FlagState


@pytest.mark.django_db
def test_staff_can_save_targeting_document_from_flag_detail(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    state = FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}),
        {
            "environment": environment.key,
            "enabled": "on",
            "off_variation": off.key,
            "target_index": ["0"],
            "target_context_kind_0": "user",
            "target_variation_key_0": on.key,
            "target_values_0": "user-1",
            "fallthrough_variation_key": off.key,
        },
    )

    assert response.status_code == 302
    state.refresh_from_db()
    assert state.enabled is True
    assert state.targeting["targets"][0]["values"] == ["user-1"]
    assert AuditLog.objects.filter(action="flag.targeting.updated", flag=flag, environment=environment).exists()


@pytest.mark.django_db
def test_targeting_save_creates_approval_request_for_protected_environment(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production", requires_approval=True)
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    state = FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}),
        {
            "environment": environment.key,
            "off_variation": off.key,
            "fallthrough_variation_key": off.key,
            "reason": "Production review",
        },
    )

    assert response.status_code == 302
    state.refresh_from_db()
    assert state.targeting == {}
    approval = ApprovalRequest.objects.get(flag=flag, environment=environment)
    assert approval.proposed_change["targeting"]["fallthrough"]["variation_key"] == off.key
```

- [ ] **Step 2: Run the new dashboard tests and verify failures**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_flag_list_edit_action_opens_flag_detail tests\test_dashboard_workflows.py::test_staff_can_save_targeting_document_from_flag_detail tests\test_dashboard_workflows.py::test_targeting_save_creates_approval_request_for_protected_environment -q
```

Expected: FAIL because `flag_detail` route and view do not exist.

- [ ] **Step 3: Add dashboard routes**

In `src/django_feature_flags/dashboard/urls.py`, add before the edit route:

```python
    path("flags/<int:pk>/", views.flag_detail, name="flag_detail"),
```

- [ ] **Step 4: Add the flag detail view**

In `src/django_feature_flags/dashboard/views.py`, import:

```python
from django.db import transaction
from django_feature_flags.dashboard.targeting_forms import TargetingDocumentForm
from django_feature_flags.models import FlagState, Variation
```

Add this view:

```python
@staff_member_required(login_url="/accounts/login/")
def flag_detail(request, pk):
    flag = get_object_or_404(
        FeatureFlag.objects.select_related("project").prefetch_related("variations", "states__environment"),
        pk=pk,
    )
    environment_key = request.POST.get("environment") or request.GET.get("environment")
    states = list(flag.states.select_related("environment", "default_variation").order_by("environment__name"))
    state = _selected_state(states, environment_key)

    if request.method == "POST":
        form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state, data=request.POST)
        if form.is_valid():
            before = {"enabled": state.enabled, "targeting": state.targeting}
            proposed_change = {"enabled": form.enabled, "targeting": form.cleaned_document}
            if state.environment.requires_approval:
                create_approval_request(
                    requested_by=request.user,
                    environment=state.environment,
                    flag=flag,
                    proposed_change=proposed_change,
                    reason=form.cleaned_data.get("reason", ""),
                )
                messages.success(request, f"Approval request for {flag.key} targeting was created.")
            else:
                with transaction.atomic():
                    state.enabled = form.enabled
                    state.targeting = form.cleaned_document
                    state.save(update_fields=["enabled", "targeting", "updated_at"])
                    create_audit_log(
                        user=request.user,
                        environment=state.environment,
                        flag=flag,
                        action="flag.targeting.updated",
                        before=before,
                        after=proposed_change,
                        reason=form.cleaned_data.get("reason", ""),
                    )
                messages.success(request, f"Targeting for {flag.key} was updated.")
            return redirect(f"{request.path}?environment={state.environment.key}")
    else:
        form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state)

    return render(
        request,
        "django_feature_flags/flag_detail.html",
        {
            "flag": flag,
            "states": states,
            "state": state,
            "form": form,
            "targeting": form.initial_document(),
            "variations": flag.variations.order_by("key"),
            "available_flags": flag.project.flags.exclude(pk=flag.pk).order_by("key"),
            "segments": flag.project.segments.order_by("key"),
            "style_name": "Premium SaaS",
        },
    )


def _selected_state(states, environment_key):
    if environment_key:
        for state in states:
            if state.environment.key == environment_key:
                return state
    return states[0]
```

- [ ] **Step 5: Point flag list to detail**

In `flag_list.html`, change the row action URL from:

```django
{% url 'django_feature_flags_dashboard:flag_update' row.flag.pk %}
```

to:

```django
{% url 'django_feature_flags_dashboard:flag_detail' row.flag.pk %}
```

- [ ] **Step 6: Add a minimal template to satisfy route rendering**

Create `src/django_feature_flags/templates/django_feature_flags/flag_detail.html` with the full template in Task 7. For this task, use this minimal version:

```django
{% extends "django_feature_flags/base.html" %}

{% block content %}
<header class="dff-header">
  <div>
    <p class="dff-kicker">{{ style_name }} / Targeting</p>
    <h1>{{ flag.name }}</h1>
    <p class="dff-subtitle"><strong class="dff-code">{{ flag.key }}</strong> targeting for {{ state.environment.key }}.</p>
  </div>
</header>

<form method="post">
  {% csrf_token %}
  <input type="hidden" name="environment" value="{{ state.environment.key }}">
  <input type="hidden" name="off_variation" value="{{ state.default_variation.key }}">
  <input type="hidden" name="fallthrough_variation_key" value="{{ state.default_variation.key }}">
  <button type="submit">Save targeting</button>
</form>
{% endblock %}
```

- [ ] **Step 7: Run dashboard route and workflow tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_flag_list_edit_action_opens_flag_detail tests\test_dashboard_workflows.py::test_staff_can_save_targeting_document_from_flag_detail tests\test_dashboard_workflows.py::test_targeting_save_creates_approval_request_for_protected_environment -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/django_feature_flags/dashboard/urls.py src/django_feature_flags/dashboard/views.py src/django_feature_flags/templates/django_feature_flags/flag_list.html src/django_feature_flags/templates/django_feature_flags/flag_detail.html tests/test_dashboard.py tests/test_dashboard_workflows.py
git commit -m "feat(dashboard): add targeting detail workflow"
```

---

### Task 7: Build The LaunchDarkly-Style Targeting Tab UI

**Files:**
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`
- Modify: `src/django_feature_flags/static/django_feature_flags/dashboard.css`
- Create: `src/django_feature_flags/static/django_feature_flags/targeting.js`
- Modify: `pyproject.toml`
- Modify: `tests/test_dashboard.py`

- [ ] **Step 1: Add failing visible contract test**

Append to `tests/test_dashboard.py`:

```python
@pytest.mark.django_db
def test_flag_detail_renders_launchdarkly_style_targeting_sections(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    default = Variation.objects.create(flag=flag, key="default", name="Default", value=False, is_default=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=default)
    client.force_login(staff_user)

    response = client.get(reverse("django_feature_flags_dashboard:flag_detail", kwargs={"pk": flag.pk}))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Targeting" in content
    assert "Off variation" in content
    assert "Prerequisites" in content
    assert "Individual targets" in content
    assert "Rules" in content
    assert "Default rule" in content
    assert "Preview" in content
    assert "targeting.js" in content
```

- [ ] **Step 2: Run the visible contract test and verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_flag_detail_renders_launchdarkly_style_targeting_sections -q
```

Expected: FAIL because the minimal template lacks the targeting sections and script.

- [ ] **Step 3: Replace `flag_detail.html`**

Replace `src/django_feature_flags/templates/django_feature_flags/flag_detail.html` with:

```django
{% extends "django_feature_flags/base.html" %}
{% load static %}

{% block content %}
<header class="dff-header dff-targeting-header">
  <div>
    <p class="dff-kicker">{{ style_name }} / Targeting</p>
    <h1>{{ flag.name }}</h1>
    <p class="dff-subtitle"><strong class="dff-code">{{ flag.key }}</strong> controls who receives each variation in the selected environment.</p>
  </div>
  <div class="dff-actions">
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_update' flag.pk %}">Settings</a>
    <a class="dff-button dff-button-secondary" href="{% url 'django_feature_flags_dashboard:flag_list' %}">Back to flags</a>
  </div>
</header>

<nav class="dff-tabbar" aria-label="Flag sections">
  <span class="dff-tab dff-tab-active">Targeting</span>
  <a class="dff-tab" href="{% url 'django_feature_flags_dashboard:flag_update' flag.pk %}">Settings</a>
  <span class="dff-tab">Variations</span>
  <span class="dff-tab">Audit</span>
</nav>

<form class="dff-targeting-layout" method="post" data-targeting-form>
  {% csrf_token %}
  <input type="hidden" name="environment" value="{{ state.environment.key }}">

  <section class="dff-panel dff-targeting-panel">
    <div class="dff-targeting-section dff-targeting-section-head">
      <div>
        <span class="dff-label">Environment</span>
        <h2>{{ state.environment.name }}</h2>
      </div>
      <select onchange="window.location='?environment=' + this.value">
        {% for item in states %}
        <option value="{{ item.environment.key }}"{% if item.pk == state.pk %} selected{% endif %}>{{ item.environment.key }}</option>
        {% endfor %}
      </select>
      <label class="dff-toggle">
        <input type="checkbox" name="enabled"{% if state.enabled %} checked{% endif %}>
        <span>Targeting on</span>
      </label>
    </div>

    {% if form.errors %}
    <div class="dff-alert dff-alert-error">{{ form.errors }}</div>
    {% endif %}

    <div class="dff-targeting-section">
      <h2>Off variation</h2>
      <p>When targeting is off, serve this variation.</p>
      <select name="off_variation">
        {% for variation in variations %}
        <option value="{{ variation.key }}"{% if targeting.off_variation == variation.key %} selected{% endif %}>{{ variation.key }}</option>
        {% endfor %}
      </select>
    </div>

    <div class="dff-targeting-section" data-list="prerequisite">
      <div class="dff-section-heading-row">
        <h2>Prerequisites</h2>
        <button class="dff-button dff-button-secondary" type="button" data-add="prerequisite">Add prerequisite</button>
      </div>
      <div data-items="prerequisite">
        {% for item in targeting.prerequisites %}
        <div class="dff-builder-row">
          <input type="hidden" name="prerequisite_index" value="{{ forloop.counter0 }}">
          <select name="prerequisite_flag_key_{{ forloop.counter0 }}">
            {% for candidate in available_flags %}
            <option value="{{ candidate.key }}"{% if item.flag_key == candidate.key %} selected{% endif %}>{{ candidate.key }}</option>
            {% endfor %}
          </select>
          <input name="prerequisite_variation_key_{{ forloop.counter0 }}" value="{{ item.variation_key }}" aria-label="Variation key">
        </div>
        {% endfor %}
      </div>
    </div>

    <div class="dff-targeting-section" data-list="target">
      <div class="dff-section-heading-row">
        <h2>Individual targets</h2>
        <button class="dff-button dff-button-secondary" type="button" data-add="target">Add target</button>
      </div>
      <div data-items="target">
        {% for item in targeting.targets %}
        <div class="dff-builder-row">
          <input type="hidden" name="target_index" value="{{ forloop.counter0 }}">
          <input name="target_context_kind_{{ forloop.counter0 }}" value="{{ item.context_kind }}" aria-label="Context kind">
          <select name="target_variation_key_{{ forloop.counter0 }}">
            {% for variation in variations %}
            <option value="{{ variation.key }}"{% if item.variation_key == variation.key %} selected{% endif %}>{{ variation.key }}</option>
            {% endfor %}
          </select>
          <textarea name="target_values_{{ forloop.counter0 }}" rows="2">{% for value in item.values %}{{ value }}{% if not forloop.last %}
{% endif %}{% endfor %}</textarea>
        </div>
        {% endfor %}
      </div>
    </div>

    <div class="dff-targeting-section" data-list="rule">
      <div class="dff-section-heading-row">
        <h2>Rules</h2>
        <button class="dff-button dff-button-secondary" type="button" data-add="rule">Add rule</button>
      </div>
      <div data-items="rule">
        {% for rule in targeting.rules %}
        <div class="dff-rule-card">
          <input type="hidden" name="rule_index" value="{{ forloop.counter0 }}">
          <input type="hidden" name="rule_id_{{ forloop.counter0 }}" value="{{ rule.id }}">
          <input name="rule_description_{{ forloop.counter0 }}" value="{{ rule.description }}" aria-label="Rule description">
          <select name="rule_serve_variation_key_{{ forloop.counter0 }}">
            {% for variation in variations %}
            <option value="{{ variation.key }}"{% if rule.serve.variation_key == variation.key %} selected{% endif %}>{{ variation.key }}</option>
            {% endfor %}
          </select>
          {% for clause in rule.clauses %}
          <div class="dff-builder-row">
            <input type="hidden" name="rule_clause_index_{{ forloop.parentloop.counter0 }}" value="{{ forloop.counter0 }}">
            <input name="rule_clause_context_kind_{{ forloop.parentloop.counter0 }}_{{ forloop.counter0 }}" value="{{ clause.context_kind }}" aria-label="Clause context kind">
            <input name="rule_clause_attribute_{{ forloop.parentloop.counter0 }}_{{ forloop.counter0 }}" value="{{ clause.attribute }}" aria-label="Clause attribute">
            <select name="rule_clause_operator_{{ forloop.parentloop.counter0 }}_{{ forloop.counter0 }}">
              <option value="{{ clause.operator }}">{{ clause.operator }}</option>
              <option value="equals">equals</option>
              <option value="in">in</option>
              <option value="segment_match">segment_match</option>
            </select>
            <input name="rule_clause_values_{{ forloop.parentloop.counter0 }}_{{ forloop.counter0 }}" value="{{ clause.values|join:', ' }}" aria-label="Clause values">
          </div>
          {% endfor %}
        </div>
        {% endfor %}
      </div>
    </div>

    <div class="dff-targeting-section">
      <h2>Default rule</h2>
      <select name="fallthrough_variation_key">
        {% for variation in variations %}
        <option value="{{ variation.key }}"{% if targeting.fallthrough.variation_key == variation.key %} selected{% endif %}>{{ variation.key }}</option>
        {% endfor %}
      </select>
    </div>

    <div class="dff-targeting-section">
      <h2>Change reason</h2>
      <textarea name="reason" rows="2" aria-label="Reason for audit or approval"></textarea>
    </div>

    <div class="dff-form-actions">
      <button class="dff-button dff-button-primary" type="submit">Save targeting</button>
    </div>
  </section>

  <aside class="dff-panel dff-targeting-preview">
    <h2>Preview</h2>
    <p>Use a multi-context JSON payload to check the matched rule and variation before saving.</p>
    <textarea name="preview_context" rows="12">{"user":{"key":"user-123"},"device":{"key":"device-1","platform":"ios"}}</textarea>
    <button class="dff-button dff-button-secondary" type="submit" formaction="{% url 'django_feature_flags_dashboard:flag_targeting_preview' flag.pk %}">Preview</button>
  </aside>
</form>

<script src="{% static 'django_feature_flags/targeting.js' %}"></script>
{% endblock %}
```

- [ ] **Step 4: Add Targeting tab CSS**

Append to `dashboard.css`:

```css
.dff-tabbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 18px;
}

.dff-tab {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--dff-line);
  border-radius: 8px;
  padding: 0 12px;
  color: var(--dff-text);
  text-decoration: none;
  font-weight: 800;
}

.dff-tab-active {
  border-color: var(--dff-line-strong);
  background: rgba(113, 246, 188, 0.12);
}

.dff-targeting-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
}

.dff-targeting-section {
  padding: 20px;
  border-bottom: 1px solid var(--dff-line);
}

.dff-targeting-section:last-child {
  border-bottom: 0;
}

.dff-targeting-section-head,
.dff-section-heading-row,
.dff-builder-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dff-section-heading-row {
  justify-content: space-between;
  margin-bottom: 12px;
}

.dff-builder-row,
.dff-rule-card {
  border: 1px solid var(--dff-line);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  margin-top: 10px;
}

.dff-rule-card {
  display: grid;
  gap: 10px;
}

.dff-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 900;
}

.dff-targeting-preview {
  position: sticky;
  top: 24px;
  padding: 18px;
}

.dff-targeting-layout input,
.dff-targeting-layout select,
.dff-targeting-layout textarea {
  max-width: 100%;
}

@media (max-width: 980px) {
  .dff-targeting-layout {
    grid-template-columns: 1fr;
  }

  .dff-targeting-preview {
    position: static;
  }

  .dff-builder-row {
    align-items: stretch;
    flex-direction: column;
  }
}
```

- [ ] **Step 5: Create `targeting.js`**

Create `src/django_feature_flags/static/django_feature_flags/targeting.js`:

```javascript
(function () {
  function nextIndex(container, name) {
    return container.querySelectorAll('[name="' + name + '_index"]').length;
  }

  function addTarget(button) {
    var section = button.closest('[data-list="target"]');
    var container = section.querySelector('[data-items="target"]');
    var index = nextIndex(container, 'target');
    var row = document.createElement('div');
    row.className = 'dff-builder-row';
    row.innerHTML = [
      '<input type="hidden" name="target_index" value="' + index + '">',
      '<input name="target_context_kind_' + index + '" value="user" aria-label="Context kind">',
      '<input name="target_variation_key_' + index + '" aria-label="Variation key">',
      '<textarea name="target_values_' + index + '" rows="2" aria-label="Target keys"></textarea>'
    ].join('');
    container.appendChild(row);
  }

  function addPrerequisite(button) {
    var section = button.closest('[data-list="prerequisite"]');
    var container = section.querySelector('[data-items="prerequisite"]');
    var index = nextIndex(container, 'prerequisite');
    var row = document.createElement('div');
    row.className = 'dff-builder-row';
    row.innerHTML = [
      '<input type="hidden" name="prerequisite_index" value="' + index + '">',
      '<input name="prerequisite_flag_key_' + index + '" aria-label="Prerequisite flag key">',
      '<input name="prerequisite_variation_key_' + index + '" aria-label="Prerequisite variation key">'
    ].join('');
    container.appendChild(row);
  }

  function addRule(button) {
    var section = button.closest('[data-list="rule"]');
    var container = section.querySelector('[data-items="rule"]');
    var index = nextIndex(container, 'rule');
    var card = document.createElement('div');
    card.className = 'dff-rule-card';
    card.innerHTML = [
      '<input type="hidden" name="rule_index" value="' + index + '">',
      '<input type="hidden" name="rule_id_' + index + '" value="rule-' + index + '">',
      '<input name="rule_description_' + index + '" aria-label="Rule description">',
      '<input name="rule_serve_variation_key_' + index + '" aria-label="Rule variation key">',
      '<div class="dff-builder-row">',
      '<input type="hidden" name="rule_clause_index_' + index + '" value="0">',
      '<input name="rule_clause_context_kind_' + index + '_0" value="user" aria-label="Clause context kind">',
      '<input name="rule_clause_attribute_' + index + '_0" aria-label="Clause attribute">',
      '<select name="rule_clause_operator_' + index + '_0"><option value="equals">equals</option><option value="in">in</option><option value="segment_match">segment_match</option></select>',
      '<input name="rule_clause_values_' + index + '_0" aria-label="Clause values">',
      '</div>'
    ].join('');
    container.appendChild(card);
  }

  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-add]');
    if (!button) {
      return;
    }
    event.preventDefault();
    if (button.dataset.add === 'target') {
      addTarget(button);
    }
    if (button.dataset.add === 'prerequisite') {
      addPrerequisite(button);
    }
    if (button.dataset.add === 'rule') {
      addRule(button);
    }
  });
})();
```

- [ ] **Step 6: Include JavaScript in package data**

In `pyproject.toml`, update package data:

```toml
django_feature_flags = [
  "templates/django_feature_flags/*.html",
  "static/django_feature_flags/*.css",
  "static/django_feature_flags/*.js",
]
```

- [ ] **Step 7: Run dashboard visible contract test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard.py::test_flag_detail_renders_launchdarkly_style_targeting_sections -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml src/django_feature_flags/templates/django_feature_flags/flag_detail.html src/django_feature_flags/static/django_feature_flags/dashboard.css src/django_feature_flags/static/django_feature_flags/targeting.js tests/test_dashboard.py
git commit -m "feat(dashboard): render targeting tab"
```

---

### Task 8: Add Preview Workflow

**Files:**
- Modify: `src/django_feature_flags/dashboard/urls.py`
- Modify: `src/django_feature_flags/dashboard/views.py`
- Modify: `src/django_feature_flags/templates/django_feature_flags/flag_detail.html`
- Modify: `src/django_feature_flags/evaluation/evaluator.py`
- Modify: `tests/test_dashboard_workflows.py`

- [ ] **Step 1: Add failing preview test**

Append to `tests/test_dashboard_workflows.py`:

```python
@pytest.mark.django_db
def test_targeting_preview_evaluates_unsaved_document(client, staff_user):
    project = Project.objects.create(key="ecommerce", name="Ecommerce")
    environment = Environment.objects.create(project=project, key="production", name="Production")
    flag = FeatureFlag.objects.create(project=project, key="checkout", name="Checkout", value_type="boolean")
    off = Variation.objects.create(flag=flag, key="off", value=False, is_default=True)
    on = Variation.objects.create(flag=flag, key="on", value=True)
    FlagState.objects.create(flag=flag, environment=environment, enabled=False, default_variation=off)
    client.force_login(staff_user)

    response = client.post(
        reverse("django_feature_flags_dashboard:flag_targeting_preview", kwargs={"pk": flag.pk}),
        {
            "environment": environment.key,
            "enabled": "on",
            "off_variation": off.key,
            "target_index": ["0"],
            "target_context_kind_0": "user",
            "target_variation_key_0": on.key,
            "target_values_0": "user-1",
            "fallthrough_variation_key": off.key,
            "preview_context": '{"user":{"key":"user-1"}}',
        },
    )

    assert response.status_code == 200
    content = response.content.decode()
    assert "Preview result" in content
    assert "target_match" in content
    assert "on" in content
```

- [ ] **Step 2: Run preview test and verify failure**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard_workflows.py::test_targeting_preview_evaluates_unsaved_document -q
```

Expected: FAIL because `flag_targeting_preview` route does not exist.

- [ ] **Step 3: Add evaluator override parameter**

In `evaluate`, add optional parameters:

```python
def evaluate(flag_key, context, default=None, project_key="default", environment_key="production", track=False, targeting_override=None, enabled_override=None):
```

When building the document:

```python
    document = targeting_override if targeting_override is not None else normalized_targeting(state)
    state_enabled = state.enabled if enabled_override is None else enabled_override
```

Use `state_enabled` instead of `state.enabled`.

- [ ] **Step 4: Add preview route**

In `dashboard/urls.py`, add:

```python
    path("flags/<int:pk>/targeting/preview/", views.flag_targeting_preview, name="flag_targeting_preview"),
```

- [ ] **Step 5: Add preview view**

In `dashboard/views.py`, import `json` is already present and add:

```python
from django_feature_flags.evaluation.evaluator import evaluate
```

Add:

```python
@staff_member_required(login_url="/accounts/login/")
def flag_targeting_preview(request, pk):
    flag = get_object_or_404(FeatureFlag.objects.select_related("project"), pk=pk)
    state = get_object_or_404(
        FlagState.objects.select_related("environment", "default_variation"),
        flag=flag,
        environment__key=request.POST.get("environment", ""),
    )
    form = TargetingDocumentForm(flag=flag, environment=state.environment, state=state, data=request.POST)
    preview_error = ""
    preview_result = None
    if form.is_valid():
        try:
            preview_context = json.loads(request.POST.get("preview_context", "{}") or "{}")
        except json.JSONDecodeError:
            preview_error = "Preview context must be valid JSON."
        else:
            preview_result = evaluate(
                flag.key,
                preview_context,
                default=None,
                project_key=flag.project.key,
                environment_key=state.environment.key,
                targeting_override=form.cleaned_document,
                enabled_override=form.enabled,
            )
    states = list(flag.states.select_related("environment", "default_variation").order_by("environment__name"))
    return render(
        request,
        "django_feature_flags/flag_detail.html",
        {
            "flag": flag,
            "states": states,
            "state": state,
            "form": form,
            "targeting": form.cleaned_document or form.initial_document(),
            "variations": flag.variations.order_by("key"),
            "available_flags": flag.project.flags.exclude(pk=flag.pk).order_by("key"),
            "segments": flag.project.segments.order_by("key"),
            "preview_result": preview_result,
            "preview_error": preview_error,
            "style_name": "Premium SaaS",
        },
    )
```

- [ ] **Step 6: Render preview result**

In `flag_detail.html`, inside `.dff-targeting-preview` after the preview button, add:

```django
    {% if preview_error %}
    <div class="dff-alert dff-alert-error">{{ preview_error }}</div>
    {% endif %}
    {% if preview_result %}
    <div class="dff-preview-result">
      <h3>Preview result</h3>
      <dl>
        <dt>Variation</dt>
        <dd>{{ preview_result.variation_key }}</dd>
        <dt>Reason</dt>
        <dd>{{ preview_result.reason }}</dd>
        <dt>Value</dt>
        <dd><code>{{ preview_result.value }}</code></dd>
      </dl>
    </div>
    {% endif %}
```

- [ ] **Step 7: Run preview test**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_dashboard_workflows.py::test_targeting_preview_evaluates_unsaved_document -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/django_feature_flags/dashboard/urls.py src/django_feature_flags/dashboard/views.py src/django_feature_flags/templates/django_feature_flags/flag_detail.html src/django_feature_flags/evaluation/evaluator.py tests/test_dashboard_workflows.py
git commit -m "feat(dashboard): preview targeting results"
```

---

### Task 9: Add Segment Matching And Prerequisite Coverage

**Files:**
- Modify: `src/django_feature_flags/targeting/operators.py`
- Modify: `src/django_feature_flags/evaluation/evaluator.py`
- Modify: `tests/test_evaluator.py`

- [ ] **Step 1: Add failing evaluator tests**

Append to `tests/test_evaluator.py`:

```python
from django_feature_flags.models import Segment, SegmentRule


@pytest.mark.django_db
def test_rule_can_match_segment_clause(flag_setup):
    project, environment, flag, off, on = flag_setup
    segment = Segment.objects.create(project=project, key="beta_users", name="Beta Users")
    SegmentRule.objects.create(segment=segment, conditions=[{"attribute": "plan", "operator": "equals", "value": "pro"}])
    state = flag.states.get(environment=environment)
    state.enabled = True
    state.targeting = {
        "off_variation": off.key,
        "targets": [],
        "rules": [
            {
                "id": "segment-rule",
                "clauses": [
                    {"context_kind": "user", "attribute": "segment", "operator": "segment_match", "values": ["beta_users"], "negate": False}
                ],
                "serve": {"variation_key": on.key},
            }
        ],
        "fallthrough": {"variation_key": off.key},
    }
    state.save(update_fields=["enabled", "targeting"])

    result = evaluate("new_checkout", {"key": "user-1", "plan": "pro"}, default=False, project_key=project.key, environment_key=environment.key)

    assert result.value is True
    assert result.reason == "rule_match"


@pytest.mark.django_db
def test_prerequisite_failure_serves_fallthrough(flag_setup):
    project, environment, flag, off, on = flag_setup
    prereq = FeatureFlag.objects.create(project=project, key="account_ready", name="Account Ready", value_type="boolean")
    prereq_off = Variation.objects.create(flag=prereq, key="off", value=False, is_default=True)
    Variation.objects.create(flag=prereq, key="on", value=True)
    FlagState.objects.create(flag=prereq, environment=environment, enabled=False, default_variation=prereq_off)
    state = flag.states.get(environment=environment)
    state.enabled = True
    state.targeting = {
        "off_variation": off.key,
        "prerequisites": [{"flag_key": "account_ready", "variation_key": "on"}],
        "targets": [{"context_kind": "user", "variation_key": on.key, "values": ["user-1"]}],
        "rules": [],
        "fallthrough": {"variation_key": off.key},
    }
    state.save(update_fields=["enabled", "targeting"])

    result = evaluate("new_checkout", {"key": "user-1"}, default=False, project_key=project.key, environment_key=environment.key)

    assert result.value is False
    assert result.reason == "prerequisite_failed"
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_evaluator.py::test_rule_can_match_segment_clause tests\test_evaluator.py::test_prerequisite_failure_serves_fallthrough -q
```

Expected: FAIL because segment clauses and prerequisites are not evaluated.

- [ ] **Step 3: Add segment clause matching**

In `operators.py`, add:

```python
def segment_clause_matches(context, clause, project):
    segment_keys = clause.get("values", [])
    for segment in project.segments.filter(key__in=segment_keys).prefetch_related("rules"):
        include = True
        for rule in segment.rules.all():
            matched = conditions_match(normalize_contexts(context).get(clause.get("context_kind", "user"), {}), rule.conditions)
            if rule.exclude and matched:
                include = False
            if not rule.exclude and not matched:
                include = False
        if include:
            return not clause.get("negate", False)
    return bool(clause.get("negate", False))
```

Update `clauses_match` signature:

```python
def clauses_match(context, clauses, project=None):
    for clause in clauses:
        if clause.get("operator") == "segment_match":
            if project is None or not segment_clause_matches(context, clause, project):
                return False
        elif not clause_matches(context, clause):
            return False
    return True
```

- [ ] **Step 4: Pass project into rule matching**

In evaluator `evaluate_rules`, call:

```python
if clauses_match(context, rule.get("clauses", []), project=flag.project):
```

- [ ] **Step 5: Add prerequisite evaluation**

In `evaluator.py`, add:

```python
def prerequisites_match(environment, flag, document, context):
    for item in document.get("prerequisites", []):
        result = evaluate(
            item.get("flag_key", ""),
            context,
            default=None,
            project_key=flag.project.key,
            environment_key=environment.key,
            track=False,
        )
        if result.variation_key != item.get("variation_key"):
            return False
    return True
```

In `evaluate`, after enabled check and before targets:

```python
    if not prerequisites_match(environment, flag, document, context):
        fallthrough_result = serve_result(environment, flag, document.get("fallthrough", {}), context, "prerequisite_failed", track)
        if fallthrough_result is not None:
            return fallthrough_result
        return tracked_result(environment, flag, state.default_variation, context, "prerequisite_failed", track)
```

- [ ] **Step 6: Run evaluator tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests\test_evaluator.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/django_feature_flags/targeting/operators.py src/django_feature_flags/evaluation/evaluator.py tests/test_evaluator.py
git commit -m "feat(targeting): support segments and prerequisites"
```

---

### Task 10: Regression Run And Documentation

**Files:**
- Modify: `README.md`
- Test: full test suite

- [ ] **Step 1: Add dashboard targeting usage to README**

Append to `README.md`:

````markdown
## Dashboard Targeting

Open `/flags/flags/`, choose a flag, and use the Targeting tab to configure one environment at a time. The dashboard supports targeting on/off state, off variation, prerequisites, individual targets across context kinds, segment clauses, custom rules, default variation, and preview evaluation with multi-context JSON.

Example preview context:

```json
{
  "user": {"key": "user-123", "plan": "pro"},
  "device": {"key": "phone-1", "platform": "ios"},
  "organization": {"key": "org-9", "tier": "enterprise"}
}
```
````

- [ ] **Step 2: Run the full test suite**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run Django system checks**

Run:

```powershell
.venv\Scripts\python.exe -m django check --settings tests.settings
```

Expected: `System check identified no issues`.

- [ ] **Step 4: Inspect changed files**

Run:

```bash
git status --short
git diff --stat
```

Expected: only files listed in this implementation plan are modified.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: explain dashboard targeting"
```

---

## Self-Review Checklist

- Spec coverage: tasks cover persistence, targeting document validation, multi-context matching, weighted rollout selection, evaluator behavior, dashboard save workflow, approvals, audit, preview, segment matching, prerequisites, UI, package data, docs, and full regression.
- Test-first flow: every runtime change starts with failing tests and a targeted command.
- Compatibility: `state.targeting == {}` keeps legacy defaults and global `TargetingRule` behavior until a per-environment document exists.
- Scope: management API clone, progressive rollouts, guarded rollouts, external SDK streaming, code references, and RBAC remain outside this implementation plan.
