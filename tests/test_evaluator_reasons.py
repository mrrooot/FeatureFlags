"""Evaluation-reason coverage for branches not exercised elsewhere.

Complements tests/test_evaluator.py (which covers off, flag_not_found,
target_match, rule_match, prerequisite_failed) with the remaining reasons:
not-found paths, emergency override, invalid targeting, prerequisite success,
prerequisite cycles, ignored draft experiments, and the rollout paths.
"""
import pytest

from django_feature_flags.evaluation.evaluator import evaluate
from django_feature_flags.models import (
    Environment,
    Experiment,
    ExperimentAllocation,
    FeatureFlag,
    FlagState,
    Project,
    Variation,
)

BOOL = [("off", False, True), ("on", True, False)]


@pytest.fixture
def env():
    project = Project.objects.create(key="p", name="P")
    environment = Environment.objects.create(project=project, key="production", name="Prod")
    return project, environment


@pytest.fixture
def make_flag(env):
    project, environment = env

    def _make(key, variations=BOOL, value_type="boolean", enabled=True, targeting=None,
              rollout=None, emergency=None, make_state=True):
        flag = FeatureFlag.objects.create(project=project, key=key, name=key, value_type=value_type)
        default = None
        for vkey, value, is_default in variations:
            variation = Variation.objects.create(flag=flag, key=vkey, value=value, is_default=is_default)
            if is_default:
                default = variation
        if make_state:
            FlagState.objects.create(
                flag=flag, environment=environment, enabled=enabled, default_variation=default,
                targeting=targeting or {}, rollout=rollout or {}, emergency_override=emergency or {},
            )
        return flag

    return _make


def ev(flag_key, context, default=None):
    return evaluate(flag_key, context, default=default, project_key="p", environment_key="production")


@pytest.mark.django_db
def test_project_not_found_returns_default(make_flag):
    make_flag("f")
    result = evaluate("f", {"key": "u"}, default="D", project_key="ghost", environment_key="production")
    assert result.value == "D"
    assert result.reason == "project_not_found"


@pytest.mark.django_db
def test_environment_not_found_returns_default(make_flag):
    make_flag("f")
    result = evaluate("f", {"key": "u"}, default="D", project_key="p", environment_key="ghost")
    assert result.value == "D"
    assert result.reason == "environment_not_found"


@pytest.mark.django_db
def test_state_not_found_returns_default(make_flag):
    make_flag("f", make_state=False)  # flag + variations, but no FlagState for the environment
    result = ev("f", {"key": "u"}, default="D")
    assert result.value == "D"
    assert result.reason == "state_not_found"


@pytest.mark.django_db
def test_emergency_override_beats_disabled(make_flag):
    make_flag("f", enabled=False, emergency={"variation_key": "on"})
    result = ev("f", {"key": "u"})
    assert result.value is True
    assert result.reason == "emergency_override"


@pytest.mark.django_db
def test_invalid_targeting_serves_state_default(make_flag):
    make_flag("f", enabled=True, targeting={"off_variation": "ghost"})  # ghost is not a variation
    result = ev("f", {"key": "u"})
    assert result.value is False  # falls back to the state default variation
    assert result.reason == "invalid_targeting"


@pytest.mark.django_db
def test_prerequisite_success_allows_target(make_flag):
    make_flag("child_on", targeting={"off_variation": "off", "fallthrough": {"variation_key": "on"}})
    make_flag("parent", targeting={
        "off_variation": "off",
        "prerequisites": [{"flag_key": "child_on", "variation_key": "on"}],
        "targets": [{"context_kind": "user", "variation_key": "on", "values": ["u1"]}],
        "fallthrough": {"variation_key": "off"},
    })
    result = ev("parent", {"key": "u1"})
    assert result.value is True
    assert result.reason == "target_match"


@pytest.mark.django_db
def test_prerequisite_cycle_terminates_safely(make_flag):
    make_flag("cyc_a", targeting={
        "off_variation": "off", "prerequisites": [{"flag_key": "cyc_b", "variation_key": "on"}],
        "fallthrough": {"variation_key": "off"}})
    make_flag("cyc_b", targeting={
        "off_variation": "off", "prerequisites": [{"flag_key": "cyc_a", "variation_key": "on"}],
        "fallthrough": {"variation_key": "off"}})
    # Must not recurse forever; resolves to a safe deterministic result.
    result = ev("cyc_a", {"key": "u"})
    assert result.value is False
    assert result.reason == "prerequisite_failed"


@pytest.mark.django_db
def test_draft_experiment_is_ignored(make_flag):
    flag = make_flag("f_exp", targeting={})
    off = flag.variations.get(key="off")
    on = flag.variations.get(key="on")
    experiment = Experiment.objects.create(flag=flag, key="e", name="E", status=Experiment.DRAFT)
    ExperimentAllocation.objects.create(experiment=experiment, variation=on, weight=100000)
    result = ev("f_exp", {"key": "u"})
    assert result.value is False  # draft experiment not applied -> default
    assert result.reason == "fallthrough"
    assert off  # sanity: default variation exists


@pytest.mark.django_db
def test_rollout_full_percentage_serves_variation(make_flag):
    make_flag("f", targeting={}, rollout={"percentage": 100, "variation_key": "on"})
    result = ev("f", {"key": "anyone"})
    assert result.value is True
    assert result.reason == "rollout"


@pytest.mark.django_db
def test_rollout_zero_percentage_falls_through(make_flag):
    make_flag("f", targeting={}, rollout={"percentage": 0, "variation_key": "on"})
    result = ev("f", {"key": "anyone"})
    assert result.value is False
    assert result.reason == "fallthrough"


@pytest.mark.django_db
def test_fallthrough_weighted_rollout_selects_variation(make_flag):
    make_flag("f", targeting={
        "off_variation": "off",
        "fallthrough": {"rollout": {"context_kind": "user", "salt": "s", "variations": [
            {"variation_key": "on", "weight": 100000},
            {"variation_key": "off", "weight": 0},
        ]}},
    })
    result = ev("f", {"key": "anyone"})
    assert result.value is True
    assert result.reason == "fallthrough"


@pytest.mark.django_db
def test_target_miss_falls_through(make_flag):
    make_flag("f", targeting={
        "off_variation": "off",
        "targets": [{"context_kind": "user", "variation_key": "on", "values": ["vip"]}],
        "fallthrough": {"variation_key": "off"},
    })
    result = ev("f", {"key": "not-vip"})
    assert result.value is False
    assert result.reason == "fallthrough"


@pytest.mark.django_db
@pytest.mark.parametrize("plan,expected_value,expected_reason", [
    ("pro", True, "rule_match"),
    ("free", False, "fallthrough"),
])
def test_rule_equals_operator_through_engine(make_flag, plan, expected_value, expected_reason):
    make_flag("f", targeting={
        "off_variation": "off",
        "rules": [{
            "id": "r", "serve": {"variation_key": "on"},
            "clauses": [{"context_kind": "user", "attribute": "plan", "operator": "equals", "values": ["pro"]}],
        }],
        "fallthrough": {"variation_key": "off"},
    })
    result = ev("f", {"key": "u", "plan": plan})
    assert result.value is expected_value
    assert result.reason == expected_reason


@pytest.mark.django_db
@pytest.mark.parametrize("flag_key,context,cache_enabled", [
    ("f", {"key": "vip"}, True),
])
def test_cache_on_and_off_agree_across_branches(make_flag, settings, flag_key, context, cache_enabled):
    """The cached and uncached paths must return identical (value, reason)."""
    make_flag("f", targeting={
        "off_variation": "off",
        "targets": [{"context_kind": "user", "variation_key": "on", "values": ["vip"]}],
        "rules": [{"id": "r", "serve": {"variation_key": "on"},
                    "clauses": [{"context_kind": "user", "attribute": "plan", "operator": "equals", "values": ["pro"]}]}],
        "fallthrough": {"variation_key": "off"},
    })
    contexts = [{"key": "vip"}, {"key": "u", "plan": "pro"}, {"key": "u", "plan": "free"}]

    settings.DJANGO_FEATURE_FLAGS_CACHE_ENABLED = True
    cached = [ev("f", c) for c in contexts]
    settings.DJANGO_FEATURE_FLAGS_CACHE_ENABLED = False
    uncached = [ev("f", c) for c in contexts]

    for a, b in zip(cached, uncached):
        assert (a.value, a.reason) == (b.value, b.reason)
