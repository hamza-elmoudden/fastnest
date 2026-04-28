import inspect
from functools import lru_cache


@lru_cache(maxsize=1024)
def _is_coroutine_function(func) -> bool:
    
    return inspect.iscoroutinefunction(func)


async def maybe_await(value):
    
    if inspect.isawaitable(value):
        return await value
    return value


async def call_sync_or_async(func, *args, **kwargs):
    
    if _is_coroutine_function(func):
        return await func(*args, **kwargs)

    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result