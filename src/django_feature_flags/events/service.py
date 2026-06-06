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

