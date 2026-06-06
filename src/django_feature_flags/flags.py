from django_feature_flags.evaluation.evaluator import evaluate


def variation(flag_key, context, default=None, project="default", environment="production", track=False):
    return evaluate(
        flag_key,
        context,
        default=default,
        project_key=project,
        environment_key=environment,
        track=track,
    ).value


def bool_variation(flag_key, context, default=False, project="default", environment="production", track=False):
    return bool(variation(flag_key, context, default=default, project=project, environment=environment, track=track))


def string_variation(flag_key, context, default="", project="default", environment="production", track=False):
    value = variation(flag_key, context, default=default, project=project, environment=environment, track=track)
    return str(value)


def number_variation(flag_key, context, default=0, project="default", environment="production", track=False):
    value = variation(flag_key, context, default=default, project=project, environment=environment, track=track)
    return value


def json_variation(flag_key, context, default=None, project="default", environment="production", track=False):
    fallback = {} if default is None else default
    return variation(flag_key, context, default=fallback, project=project, environment=environment, track=track)
