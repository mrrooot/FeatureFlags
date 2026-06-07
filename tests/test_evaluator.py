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
    assert result.reason == "off"


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
