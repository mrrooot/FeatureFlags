"""Exhaustive coverage of the comparison operators and clause matching."""
import pytest

from django_feature_flags.targeting.operators import clause_matches, compare


@pytest.mark.parametrize("actual,operator,expected,want", [
    ("a", "equals", "a", True),
    ("a", "equals", "b", False),
    ("a", "not_equals", "b", True),
    ("a", "not_equals", "a", False),
    ("hello", "contains", "ell", True),
    ("hello", "contains", "z", False),
    ("b", "in", ["a", "b"], True),
    ("c", "in", ["a", "b"], False),
    ("c", "not_in", ["a", "b"], True),
    ("a", "not_in", ["a", "b"], False),
    ("abcz", "matches", "^a.*z$", True),
    ("abc", "matches", "^a.*z$", False),
    (5, "greater_than", 3, True),
    (3, "greater_than", 5, False),
    (5, "greater_than_or_equal", 5, True),
    (4, "greater_than_or_equal", 5, False),
    (3, "less_than", 5, True),
    (5, "less_than", 3, False),
    (5, "less_than_or_equal", 5, True),
    (6, "less_than_or_equal", 5, False),
    ("2020-01-01", "before", "2021-01-01", True),
    ("2022-01-01", "before", "2021-01-01", False),
    ("2022-01-01", "after", "2021-01-01", True),
    ("2020-01-01", "after", "2021-01-01", False),
    ("a", "unknown_operator", "a", False),
])
def test_compare_operator(actual, operator, expected, want):
    assert compare(actual, operator, expected) is want


def test_contains_handles_none_actual():
    assert compare(None, "contains", "x") is False


def test_matches_handles_none_actual():
    assert compare(None, "matches", ".*") is False


def test_clause_matches_uses_first_value_for_scalar_operator():
    clause = {"context_kind": "user", "attribute": "plan", "operator": "equals", "values": ["pro"]}
    assert clause_matches({"user": {"key": "u", "plan": "pro"}}, clause) is True
    assert clause_matches({"user": {"key": "u", "plan": "free"}}, clause) is False


def test_clause_matches_uses_full_list_for_membership_operator():
    clause = {"context_kind": "user", "attribute": "country", "operator": "in", "values": ["US", "CA"]}
    assert clause_matches({"user": {"key": "u", "country": "CA"}}, clause) is True
    assert clause_matches({"user": {"key": "u", "country": "MX"}}, clause) is False


def test_clause_negate_inverts_match():
    clause = {"context_kind": "user", "attribute": "plan", "operator": "equals", "values": ["pro"], "negate": True}
    assert clause_matches({"user": {"key": "u", "plan": "free"}}, clause) is True
    assert clause_matches({"user": {"key": "u", "plan": "pro"}}, clause) is False
