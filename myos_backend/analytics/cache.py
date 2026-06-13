from django.core.cache import cache


def metric_cache_key(prefix, user):
    return f"analytics:{prefix}:user:{user.pk}"


def cache_metric(prefix, user, builder, timeout=300):
    key = metric_cache_key(prefix, user)
    cached = cache.get(key)
    if cached is not None:
        return cached
    payload = builder()
    cache.set(key, payload, timeout=timeout)
    return payload
