"""
Metadata storage — attached directly to classes/functions.
No global state → no leaks, no test pollution, full inheritance support.
"""
from typing import Any, Optional
import inspect


_META_ATTR = "__fastnest_meta__"


def set_meta(target: Any, key: str, value: Any) -> None:
    """Attach metadata to a class/function."""
    if not hasattr(target, _META_ATTR) or _META_ATTR not in target.__dict__:
        # Create a fresh dict on THIS target (not inherited)
        setattr(target, _META_ATTR, {})
    target.__dict__[_META_ATTR][key] = value


def get_meta(target: Any, key: str, default: Any = None) -> Any:
    """
    Read metadata with full MRO inheritance support.
    
    - For classes: walks __mro__ (supports controller inheritance)
    - For list values: merges from all parents (e.g. guards, interceptors)
    """
    if inspect.isclass(target):
        return _get_meta_from_class(target, key, default)

    meta = getattr(target, _META_ATTR, None)
    return meta.get(key, default) if meta else default


def _get_meta_from_class(cls: type, key: str, default: Any) -> Any:
    """Walk MRO to collect metadata from parent classes."""
    collected_lists: list = []
    found_value: Any = default
    found = False

    for klass in cls.__mro__:
        if klass is object:
            continue
        meta = klass.__dict__.get(_META_ATTR)
        if not meta or key not in meta:
            continue

        value = meta[key]

        # Merge list-type metadata from entire MRO chain
        if isinstance(value, list):
            # Parent items first, then child
            collected_lists = list(value) + collected_lists
            found = True
            continue

        # Non-list: first found (closest in MRO) wins
        if not found:
            found_value = value
            found = True

    return collected_lists if collected_lists else found_value


def has_meta(target: Any, key: str) -> bool:
    return get_meta(target, key, _MISSING) is not _MISSING


class _MissingType: pass
_MISSING = _MissingType()


def clear_meta(target: Any) -> None:
    """Useful for testing."""
    if hasattr(target, _META_ATTR):
        delattr(target, _META_ATTR)