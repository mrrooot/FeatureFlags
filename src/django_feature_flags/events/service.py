from django_feature_flags.models import Event


def record_evaluation(environment, flag, variation, context, payload=None):
    return Event.objects.create(
        environment=environment,
        flag=flag,
        variation=variation,
        event_type=Event.EVALUATION,
        context_key=str(context.get("key", "")),
        payload=payload or {},
    )


def record_evaluation_ids(environment_id, flag_id, variation_id, context, payload=None):
    """Record an evaluation event using primary keys instead of instances.

    Lets the cached evaluator write tracking events without first loading the
    environment/flag/variation rows it already resolved from the config snapshot.
    """
    return Event.objects.create(
        environment_id=environment_id,
        flag_id=flag_id,
        variation_id=variation_id,
        event_type=Event.EVALUATION,
        context_key=str(context.get("key", "")),
        payload=payload or {},
    )

