from dataclasses import dataclass

from django_feature_flags.models import Environment, FeatureFlag, FlagState, Project
from django_feature_flags.targeting.operators import conditions_match
from django_feature_flags.targeting.rollout import is_in_rollout


@dataclass(frozen=True)
class EvaluationResult:
    value: object
    variation_key: str
    reason: str
    flag_key: str
    environment_key: str


def context_key(context):
    return str(context.get("key") or context.get("user", {}).get("key") or "anonymous")


def default_result(flag_key, environment_key, default, reason):
    return EvaluationResult(
        value=default,
        variation_key="",
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
    )


def variation_result(flag_key, environment_key, variation, reason):
    return EvaluationResult(
        value=variation.value,
        variation_key=variation.key,
        reason=reason,
        flag_key=flag_key,
        environment_key=environment_key,
    )


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
            return variation_result(flag.key, environment.key, variation, "emergency_override")

    if not state.enabled:
        return variation_result(flag.key, environment.key, state.default_variation, "disabled")

    for rule in flag.targeting_rules.select_related("variation").order_by("priority", "id"):
        if conditions_match(context, rule.conditions):
            return variation_result(flag.key, environment.key, rule.variation, "target_match")

    rollout = state.rollout or {}
    if rollout.get("percentage") and rollout.get("variation_key"):
        if is_in_rollout(flag.key, context_key(context), rollout["percentage"], salt=environment.key):
            variation = flag.variations.filter(key=rollout["variation_key"]).first()
            if variation is not None:
                return variation_result(flag.key, environment.key, variation, "rollout")

    return variation_result(flag.key, environment.key, state.default_variation, "fallthrough")
