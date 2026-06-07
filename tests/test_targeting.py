from django_feature_flags.targeting.operators import conditions_match
from django_feature_flags.targeting.rollout import bucket_context
from django_feature_flags.targeting.operators import clause_matches, normalize_contexts
from django_feature_flags.targeting.rollout import choose_weighted_variation


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
