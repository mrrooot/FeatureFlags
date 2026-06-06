from django_feature_flags.models import Experiment
from django_feature_flags.targeting.rollout import bucket_context


def choose_experiment_variation(experiment, context):
    context_key = str(context.get("key", "anonymous"))
    bucket = bucket_context(experiment.flag.key, context_key, salt=experiment.key)
    cursor = 0
    for allocation in experiment.allocations.select_related("variation").order_by("id"):
        cursor += allocation.weight
        if bucket < cursor:
            return allocation.variation
    return None


def active_experiment_for_flag(flag):
    return flag.experiments.filter(status=Experiment.RUNNING).order_by("id").first()

