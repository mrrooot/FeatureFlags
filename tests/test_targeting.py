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
