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

    if not document.get("off_variation"):
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


def validate_targeting_document(
    document,
    *,
    variation_keys,
    segment_keys,
    other_flag_keys,
    default_variation_key="",
):
    """Validate a targeting document against pre-resolved key sets.

    This is the DB-free core of :func:`validate_targeting`. Callers that already
    hold the flag's variation/segment/sibling-flag keys (for example the cached
    evaluation config) can validate without issuing any queries.
    """
    errors = {}
    cleaned = empty_targeting(default_variation_key or "")
    cleaned.update(deepcopy(document or {}))
    variation_keys = set(variation_keys)
    segment_keys = set(segment_keys)
    other_flag_keys = set(other_flag_keys)

    _validate_variation_key(errors, "off_variation", cleaned.get("off_variation"), variation_keys)
    _validate_prerequisites(errors, cleaned.get("prerequisites", []), other_flag_keys)
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


def validate_targeting(flag, environment, document):
    return validate_targeting_document(
        document,
        variation_keys=flag.variations.values_list("key", flat=True),
        segment_keys=flag.project.segments.values_list("key", flat=True),
        other_flag_keys=flag.project.flags.exclude(pk=flag.pk).values_list("key", flat=True),
        default_variation_key=flag.variations.filter(is_default=True).values_list("key", flat=True).first() or "",
    )


def _validate_variation_key(errors, section, variation_key, variation_keys):
    if variation_key and variation_key not in variation_keys:
        errors.setdefault(section, []).append(f"Variation '{variation_key}' does not exist.")


def _validate_prerequisites(errors, prerequisites, flag_keys):
    seen = set()
    for item in prerequisites:
        flag_key = str(item.get("flag_key", "")).strip()
        variation_key = str(item.get("variation_key", "")).strip()
        if not flag_key or flag_key not in flag_keys:
            errors.setdefault("prerequisites", []).append(
                f"Prerequisite flag '{flag_key or '<missing>'}' does not exist."
            )
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
