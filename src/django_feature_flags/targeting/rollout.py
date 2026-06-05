import hashlib


def bucket_context(flag_key, context_key, salt=""):
    payload = f"{flag_key}:{context_key}:{salt}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:12], 16) % 100000


def is_in_rollout(flag_key, context_key, percentage, salt=""):
    threshold = int(float(percentage) * 1000)
    return bucket_context(flag_key, context_key, salt=salt) < threshold
