import os

from django.conf import settings as django_settings


DEFAULT_ENVIRONMENTS = ("development", "staging", "production")
SDK_KEY_PREFIX = "dff"
DEFAULT_BRAND_NAME = "Thiqal"
DEFAULT_BRAND_MARK = "TQ"
DEFAULT_BRAND_TAGLINE = "Feature flag console"
DEFAULT_BRAND_TITLE = "Thiqal Feature Flags"

# Evaluation config caching. Flag/state/variation/targeting/segment/experiment
# config is read on every evaluation; caching it removes those queries from the
# hot path. Point CACHE_ALIAS at a shared backend (Redis/Memcached) for instant
# cross-process invalidation; with a per-process cache, staleness is bounded by
# CACHE_TTL.
DEFAULT_CACHE_ALIAS = "default"
DEFAULT_CACHE_TTL = 300


def cache_enabled():
    return bool(getattr(django_settings, "DJANGO_FEATURE_FLAGS_CACHE_ENABLED", True))


def cache_alias():
    return configured_value("DJANGO_FEATURE_FLAGS_CACHE_ALIAS", DEFAULT_CACHE_ALIAS)


def cache_ttl():
    raw = getattr(django_settings, "DJANGO_FEATURE_FLAGS_CACHE_TTL", None)
    if raw is None:
        raw = os.environ.get("DJANGO_FEATURE_FLAGS_CACHE_TTL")
    if raw is None:
        return DEFAULT_CACHE_TTL
    try:
        return int(raw)
    except (TypeError, ValueError):
        return DEFAULT_CACHE_TTL


def configured_value(setting_name, default):
    configured = getattr(django_settings, setting_name, None)
    if configured is None:
        configured = os.environ.get(setting_name)
    value = str(configured if configured is not None else default).strip()
    return value or default


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


def dashboard_brand():
    return {
        "name": configured_value("DJANGO_FEATURE_FLAGS_BRAND_NAME", DEFAULT_BRAND_NAME),
        "mark": configured_value("DJANGO_FEATURE_FLAGS_BRAND_MARK", DEFAULT_BRAND_MARK),
        "tagline": configured_value("DJANGO_FEATURE_FLAGS_BRAND_TAGLINE", DEFAULT_BRAND_TAGLINE),
        "title": configured_value("DJANGO_FEATURE_FLAGS_BRAND_TITLE", DEFAULT_BRAND_TITLE),
    }
