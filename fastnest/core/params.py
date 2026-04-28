from enum import Enum
from typing import Optional, Any


class ParamType(Enum):
    BODY    = "body"
    QUERY   = "query"
    PARAM   = "param"
    HEADERS = "headers"
    REQ     = "request"


class _ParamMarker:
    __slots__ = ("type", "key", "default", "_custom_extractor", "_custom_data", "_custom_default")

    def __init__(self, type: ParamType, key: Optional[str] = None, default: Any = ...):
        self.type = type
        self.key = key
        self.default = default
        self._custom_extractor = None
        self._custom_data = None
        self._custom_default = ...

    def __repr__(self):
        return f"<{self.type.value}:{self.key or '*'}>"


# ─────────────── Public Decorators ───────────────

def Body(key: Optional[str] = None, default: Any = ...):
   
    return _ParamMarker(ParamType.BODY, key, default)


def Query(key: Optional[str] = None, default: Any = ...):
    return _ParamMarker(ParamType.QUERY, key, default)


def Param(key: Optional[str] = None, default: Any = ...):
    return _ParamMarker(ParamType.PARAM, key, default)


def Headers(key: Optional[str] = None, default: Any = ...):
    return _ParamMarker(ParamType.HEADERS, key, default)


def Req():
    return _ParamMarker(ParamType.REQ)


def is_param_marker(value) -> bool:
    return isinstance(value, _ParamMarker)