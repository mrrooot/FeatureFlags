import pytest

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project, Variation
from django_feature_flags.targeting.documents import (
    ROLLOUT_SCALE,
    TargetingValidationError,
    normalized_targeting,
    validate_targeting,
)


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
    document = {
        "off_variation": "missing",
        "prerequisites": [],
        "targets": [],
        "rules": [],
        "fallthrough": {"variation_key": "missing"},
    }

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
