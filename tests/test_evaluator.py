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
