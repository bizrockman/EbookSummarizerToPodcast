import sys

from functools import wraps
import diskcache as dc


def cache_with_disk(path="./.cache", size_limit=2 ** 25):  # 512 MB als Standardgröße
    def decorator(func):
        cache = dc.Cache(path, size_limit=size_limit)

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__ + str(args) + str(kwargs)
            if key in cache:
                item_size = sys.getsizeof(cache[key])
                return cache[key]
            else:
                result = func(*args, **kwargs)
                cache[key] = result
                return result

        # def clear_cache():
        #    cache.clear()
        #    wrapper.clear_cache = clear_cache

        return wrapper

    return decorator
