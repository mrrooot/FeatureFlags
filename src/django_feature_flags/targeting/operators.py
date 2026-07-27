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
        return actual in (expected or [])
    if operator == "not_in":
        return actual not in (expected or [])
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


def _segment_rule_sets(clause, project=None, segments=None):
    """Yield lists of {"conditions", "exclude"} for each referenced segment.

    When ``segments`` (a mapping of segment key -> rule dicts, e.g. from the
    cached evaluation config) is supplied it is used directly and no query is
    issued. Otherwise the segments are loaded from ``project`` as before.
    """
    segment_keys = clause.get("values", [])
    if segments is not None:
        for key in segment_keys:
            rules = segments.get(key)
            if rules is not None:
                yield rules
        return
    if project is None:
        return
    for segment in project.segments.filter(key__in=segment_keys).prefetch_related("rules"):
        yield [{"conditions": rule.conditions, "exclude": rule.exclude} for rule in segment.rules.all()]


def segment_clause_matches(context, clause, project=None, segments=None):
    context_kind = clause.get("context_kind", "user")
    selected_context = normalize_contexts(context).get(context_kind, {})
    for rules in _segment_rule_sets(clause, project=project, segments=segments):
        include = True
        for rule in rules:
            matched = conditions_match(selected_context, rule.get("conditions", []))
            if rule.get("exclude") and matched:
                include = False
            if not rule.get("exclude") and not matched:
                include = False
        if include:
            return not clause.get("negate", False)
    return bool(clause.get("negate", False))


def clauses_match(context, clauses, project=None, segments=None):
    for clause in clauses:
        if clause.get("operator") == "segment_match":
            if project is None and segments is None:
                return False
            if not segment_clause_matches(context, clause, project=project, segments=segments):
                return False
        elif not clause_matches(context, clause):
            return False
    return True

