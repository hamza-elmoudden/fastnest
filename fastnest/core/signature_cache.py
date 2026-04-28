import inspect
import weakref

# WeakKeyDictionary: entries are automatically removed when the function
# object is garbage-collected (e.g. during hot-reload). Prevents memory leaks.
_SIGNATURE_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()

def get_cached_signature(func):
    
    key = func.__func__ if hasattr(func, "__func__") else func

    cached = _SIGNATURE_CACHE.get(key)
    if cached is not None:
        return cached

    signature = inspect.signature(func)
    _SIGNATURE_CACHE[key] = signature
    return signature


def precompute_signature(func):
    
    get_cached_signature(func)
    return func


def clear_signature_cache():
    _SIGNATURE_CACHE.clear()