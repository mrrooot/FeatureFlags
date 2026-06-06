import os

from django.conf import settings as django_settings


DEFAULT_ENVIRONMENTS = ("development", "staging", "production")
SDK_KEY_PREFIX = "dff"


def configured_environment_keys():
    configured = getattr(django_settings, "DJANGO_FEATURE_FLAGS_ENVIRONMENTS", None)
    if configured is None:
        configured = os.environ.get("DJANGO_FEATURE_FLAGS_ENVIRONMENTS")
    if configured is None:
        configured = DEFAULT_ENVIRONMENTS

    if isinstance(configured, str):
        candidates = configured.split(",")
    else:
        candidates = configured

    keys = []
    for candidate in candidates:
        key = str(candidate).strip()
        if key and key not in keys:
            keys.append(key)

    return tuple(keys) or DEFAULT_ENVIRONMENTS


def environment_name(environment_key):
    return environment_key.replace("-", " ").replace("_", " ").title()


def configured_environment_rows():
    return [{"key": key, "name": environment_name(key)} for key in configured_environment_keys()]
