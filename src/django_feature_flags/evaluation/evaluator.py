from dataclasses import dataclass, field

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project
from django_feature_flags.targeting.documents import TargetingValidationError, normalized_targeting, validate_targeting
from django_feature_flags.targeting.operators import clauses_match, conditions_match, normalize_contexts
from django_feature_flags.targeting.rollout import choose_weighted_variation, is_in_rollout


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


def variation_result(flag_key, environment_key, variation, reason, detail=None):
    return EvaluationResult(
        value=variation.value,
        variation_key=variation.key,
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
        detail=detail or {},
    )


def tracked_result(environment, flag, variation, context, reason, track, detail=None):
    if track:
        from django_feature_flags.events.service import record_evaluation

        payload = {"reason": reason}
        if detail:
            payload["detail"] = detail
        record_evaluation(environment, flag, variation, context, payload=payload)
    return variation_result(flag.key, environment.key, variation, reason, detail=detail)


def variation_by_key(flag, variation_key):
    if not variation_key:
        return None
    return flag.variations.filter(key=variation_key).first()


def serve_result(environment, flag, serve, context, reason, track, detail=None):
    variation_key = serve.get("variation_key", "")
    if not variation_key and serve.get("rollout"):
        variation_key = choose_weighted_variation(flag.key, context, serve["rollout"])
    variation = variation_by_key(flag, variation_key)
    if variation is None:
        return None
    return tracked_result(environment, flag, variation, context, reason, track, detail=detail or {})


def evaluate_targets(environment, flag, document, context, track):
    contexts = normalize_contexts(context)
    for target in document.get("targets", []):
        context_kind = target.get("context_kind", "user")
        key = str(contexts.get(context_kind, {}).get("key", ""))
        if key and key in target.get("values", []):
            return serve_result(
                environment,
                flag,
                {"variation_key": target.get("variation_key", "")},
                context,
                "target_match",
                track,
                detail={"context_kind": context_kind, "target_key": key},
            )
    return None


def evaluate_rules(environment, flag, document, context, track):
    for rule in document.get("rules", []):
        if clauses_match(context, rule.get("clauses", [])):
            result = serve_result(
                environment,
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


def evaluate(flag_key, context, default=None, project_key="default", environment_key="production", track=False):
    project = Project.objects.filter(key=project_key).first()
    if project is None:
        return default_result(flag_key, environment_key, default, "project_not_found")

    environment = Environment.objects.filter(project=project, key=environment_key).first()
    if environment is None:
        return default_result(flag_key, environment_key, default, "environment_not_found")

    flag = FeatureFlag.objects.filter(project=project, key=flag_key, archived=False).first()
    if flag is None:
        return default_result(flag_key, environment.key, default, "flag_not_found")

    state = FlagState.objects.filter(flag=flag, environment=environment).select_related("default_variation").first()
    if state is None or state.default_variation is None:
        return default_result(flag_key, environment.key, default, "state_not_found")

    if state.emergency_override.get("variation_key"):
        variation = flag.variations.filter(key=state.emergency_override["variation_key"]).first()
        if variation is not None:
            return tracked_result(environment, flag, variation, context, "emergency_override", track)

    document = normalized_targeting(state)
    try:
        document = validate_targeting(flag, environment, document)
    except TargetingValidationError as exc:
        return tracked_result(
            environment,
            flag,
            state.default_variation,
            context,
            "invalid_targeting",
            track,
            detail={"errors": exc.errors},
        )

    if not state.enabled:
        variation = variation_by_key(flag, document.get("off_variation")) or state.default_variation
        return tracked_result(environment, flag, variation, context, "off", track)

    if state.targeting:
        target_result = evaluate_targets(environment, flag, document, context, track)
        if target_result is not None:
            return target_result

        rule_result = evaluate_rules(environment, flag, document, context, track)
        if rule_result is not None:
            return rule_result

        fallthrough_result = serve_result(
            environment,
            flag,
            document.get("fallthrough", {}),
            context,
            "fallthrough",
            track,
        )
        if fallthrough_result is not None:
            return fallthrough_result

    for rule in flag.targeting_rules.select_related("variation").order_by("priority", "id"):
        if conditions_match(context, rule.conditions):
            return tracked_result(environment, flag, rule.variation, context, "target_match", track)

    from django_feature_flags.experiments.service import active_experiment_for_flag, choose_experiment_variation

    experiment = active_experiment_for_flag(flag)
    if experiment is not None:
        variation = choose_experiment_variation(experiment, context)
        if variation is not None:
            return tracked_result(environment, flag, variation, context, "experiment", track)

    rollout = state.rollout or {}
    if rollout.get("percentage") and rollout.get("variation_key"):
        if is_in_rollout(flag.key, context_key(context), rollout["percentage"], salt=environment.key):
            variation = flag.variations.filter(key=rollout["variation_key"]).first()
            if variation is not None:
                return tracked_result(environment, flag, variation, context, "rollout", track)

    return tracked_result(environment, flag, state.default_variation, context, "fallthrough", track)
