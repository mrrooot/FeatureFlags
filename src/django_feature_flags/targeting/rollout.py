import hashlib


def bucket_context(flag_key, context_key, salt=""):
    payload = f"{flag_key}:{context_key}:{salt}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:12], 16) % 100000


def is_in_rollout(flag_key, context_key, percentage, salt=""):
    threshold = int(float(percentage) * 1000)
    return bucket_context(flag_key, context_key, salt=salt) < threshold


def choose_weighted_variation(flag_key, context, rollout):
    from django_feature_flags.targeting.operators import get_context_attribute

    context_kind = rollout.get("context_kind", "user")
    key = str(get_context_attribute(context, context_kind, "key") or "anonymous")
    bucket = bucket_context(flag_key, key, salt=rollout.get("salt", ""))
    running = 0
    for item in rollout.get("variations", []):
        running += int(item.get("weight", 0))
        if bucket < running:
            return item.get("variation_key", "")
    return ""
