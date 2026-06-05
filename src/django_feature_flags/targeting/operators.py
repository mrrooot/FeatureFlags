import re
from datetime import date, datetime


def get_attribute(context, attribute):
    current = context
    for part in attribute.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def compare(actual, operator, expected):
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "contains":
        return actual is not None and str(expected) in str(actual)
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "matches":
        return actual is not None and re.search(str(expected), str(actual)) is not None
    if operator == "greater_than":
        return actual > expected
    if operator == "greater_than_or_equal":
        return actual >= expected
    if operator == "less_than":
        return actual < expected
    if operator == "less_than_or_equal":
        return actual <= expected
    if operator == "before":
        return parse_datetime(actual) < parse_datetime(expected)
    if operator == "after":
        return parse_datetime(actual) > parse_datetime(expected)
    return False


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    return datetime.fromisoformat(str(value))


def conditions_match(context, conditions):
    for condition in conditions:
        actual = get_attribute(context, condition["attribute"])
        if not compare(actual, condition["operator"], condition.get("value")):
            return False
    return True

