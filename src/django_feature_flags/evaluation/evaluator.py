from dataclasses import dataclass, field

from django_feature_flags.evaluation.config import get_environment_config
from django_feature_flags.targeting.documents import TargetingValidationError, validate_targeting_document
from django_feature_flags.targeting.operators import clauses_match, conditions_match, normalize_contexts
from django_feature_flags.targeting.rollout import bucket_context, choose_weighted_variation, is_in_rollout


@dataclass(frozen=True)
class EvaluationResult:
    value: object
    variation_key: str
    reason: str
    flag_key: str
    environment_key: str
    detail: dict = field(default_factory=dict)


def context_key(context):
    return str(context.get("key") or context.get("user", {}).get("key") or "anonymous")


def default_result(flag_key, environment_key, default, reason, detail=None):
    return EvaluationResult(
        value=default,
        variation_key="",
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
        detail=detail or {},
    )


def evaluate(
    flag_key,
    context,
    default=None,
    project_key="default",
    environment_key="production",
    track=False,
    targeting_override=None,
    enabled_override=None,
    _visited=None,
):
    # Overrides come from the dashboard preview and evaluate against unsaved
    # edits, so they must not read (or populate) the shared cache.
    use_cache = targeting_override is None and enabled_override is None
    config = get_environment_config(project_key, environment_key, use_cache=use_cache)
    return _evaluate(
        config,
        flag_key,
        context,
        default=default,
        track=track,
        targeting_override=targeting_override,
        enabled_override=enabled_override,
        visited=_visited,
    )


def _evaluate(
    config,
    flag_key,
    context,
    default=None,
    track=False,
    targeting_override=None,
    enabled_override=None,
    visited=None,
):
    if not config.project_exists:
        return default_result(flag_key, config.environment_key, default, "project_not_found")
    if not config.environment_exists:
        return default_result(flag_key, config.environment_key, default, "environment_not_found")

    flag = config.flag(flag_key)
    if flag is None:
        return default_result(flag_key, config.environment_key, default, "flag_not_found")

    visited = set(visited or ())
    current_identity = (config.project_key, config.environment_key, flag.key)
    if current_identity in visited:
        return default_result(flag_key, config.environment_key, default, "prerequisite_cycle")
    visited.add(current_identity)

    if not flag.state_exists:
        return default_result(flag_key, config.environment_key, default, "state_not_found")

    emergency_key = flag.emergency_override.get("variation_key") if flag.emergency_override else ""
    if emergency_key:
        variation = flag.variations.get(emergency_key)
        if variation is not None:
            return _tracked_result(config, flag, variation, context, "emergency_override", track)

    document = targeting_override if targeting_override is not None else flag.normalized_document
    state_enabled = flag.enabled if enabled_override is None else enabled_override
    has_targeting_document = targeting_override is not None or flag.has_targeting

    try:
        document = validate_targeting_document(
            document,
            variation_keys=flag.variations.keys(),
            segment_keys=config.segments.keys(),
            other_flag_keys=config.flag_keys - {flag.key},
            default_variation_key=flag.flag_default_variation_key,
        )
    except TargetingValidationError as exc:
        variation = flag.variations.get(flag.state_default_variation_key)
        return _tracked_result(
            config, flag, variation, context, "invalid_targeting", track, detail={"errors": exc.errors}
        )

    if not state_enabled:
        variation = flag.variations.get(document.get("off_variation")) or flag.variations.get(
            flag.state_default_variation_key
        )
        return _tracked_result(config, flag, variation, context, "off", track)

    if has_targeting_document:
        if not _prerequisites_match(config, flag, document, context, visited):
            fallthrough_result = _serve_result(
                config, flag, document.get("fallthrough", {}), context, "prerequisite_failed", track
            )
            if fallthrough_result is not None:
                return fallthrough_result
            variation = flag.variations.get(flag.state_default_variation_key)
            return _tracked_result(config, flag, variation, context, "prerequisite_failed", track)

        target_result = _evaluate_targets(config, flag, document, context, track)
        if target_result is not None:
            return target_result

        rule_result = _evaluate_rules(config, flag, document, context, track)
        if rule_result is not None:
            return rule_result

        fallthrough_result = _serve_result(
            config, flag, document.get("fallthrough", {}), context, "fallthrough", track
        )
        if fallthrough_result is not None:
            return fallthrough_result

    for rule in flag.legacy_rules:
        if conditions_match(context, rule["conditions"]):
            variation = flag.variations.get(rule["variation_key"])
            if variation is not None:
                return _tracked_result(config, flag, variation, context, "target_match", track)

    if flag.experiment is not None:
        variation_key = _choose_experiment_variation(flag.experiment, context)
        if variation_key is not None:
            variation = flag.variations.get(variation_key)
            if variation is not None:
                return _tracked_result(config, flag, variation, context, "experiment", track)

    rollout = flag.rollout or {}
    if rollout.get("percentage") and rollout.get("variation_key"):
        if is_in_rollout(flag.key, context_key(context), rollout["percentage"], salt=config.environment_key):
            variation = flag.variations.get(rollout["variation_key"])
            if variation is not None:
                return _tracked_result(config, flag, variation, context, "rollout", track)

    variation = flag.variations.get(flag.state_default_variation_key)
    return _tracked_result(config, flag, variation, context, "fallthrough", track)


def _tracked_result(config, flag, variation, context, reason, track, detail=None):
    if variation is None:
        return default_result(flag.key, config.environment_key, None, reason, detail)
    if track:
        from django_feature_flags.events.service import record_evaluation_ids

        payload = {"reason": reason}
        if detail:
            payload["detail"] = detail
        record_evaluation_ids(config.environment_id, flag.id, variation.id, context, payload=payload)
    return EvaluationResult(
        value=variation.value,
        variation_key=variation.key,
        reason=reason,
        flag_key=flag.key,
        environment_key=config.environment_key,
        detail=detail or {},
    )


def _serve_result(config, flag, serve, context, reason, track, detail=None):
    variation_key = serve.get("variation_key", "")
    if not variation_key and serve.get("rollout"):
        variation_key = choose_weighted_variation(flag.key, context, serve["rollout"])
    variation = flag.variations.get(variation_key)
    if variation is None:
        return None
    return _tracked_result(config, flag, variation, context, reason, track, detail=detail or {})


def _evaluate_targets(config, flag, document, context, track):
    contexts = normalize_contexts(context)
    for target in document.get("targets", []):
        context_kind = target.get("context_kind", "user")
        key = str(contexts.get(context_kind, {}).get("key", ""))
        if key and key in target.get("values", []):
            return _serve_result(
                config,
                flag,
                {"variation_key": target.get("variation_key", "")},
                context,
                "target_match",
                track,
                detail={"context_kind": context_kind, "target_key": key},
            )
    return None


def _evaluate_rules(config, flag, document, context, track):
    for rule in document.get("rules", []):
        if clauses_match(context, rule.get("clauses", []), segments=config.segments):
            result = _serve_result(
                config,
                flag,
                rule.get("serve", {}),
                context,
                "rule_match",
                track,
                detail={"rule_id": rule.get("id", "")},
            )
            if result is not None:
                return result
    return None


def _prerequisites_match(config, flag, document, context, visited):
    for item in document.get("prerequisites", []):
        prerequisite_key = item.get("flag_key", "")
        prerequisite_identity = (config.project_key, config.environment_key, prerequisite_key)
        if prerequisite_identity in visited:
            return False
        result = _evaluate(config, prerequisite_key, context, default=None, track=False, visited=visited)
        if result.variation_key != item.get("variation_key"):
            return False
    return True


def _choose_experiment_variation(experiment, context):
    key = str(context.get("key", "anonymous"))
    bucket = bucket_context(experiment.flag_key, key, salt=experiment.key)
    cursor = 0
    for weight, variation_key in experiment.allocations:
        cursor += weight
        if bucket < cursor:
            return variation_key
    return None
