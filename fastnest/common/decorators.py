# fastnest/common/decorators.py
from typing import Any, Callable
from fastnest.core.metadata import set_meta
from fastnest.core.params import _ParamMarker, ParamType


def SetMetadata(key: str, value: Any):
    """
    Attach custom metadata to a class or method.
    Read it later via Reflector.
    """
    def decorator(target):
        set_meta(target, key, value)
        return target
    return decorator


def Roles(*roles: str):
    """Shortcut: @Roles('admin', 'user')"""
    return SetMetadata("roles", list(roles))


def Public():
    """Shortcut: mark route as public (skip auth guards)"""
    return SetMetadata("is_public", True)


# ─────────────────────────────────────────────────────
#  createParamDecorator — the NestJS-style custom param
# ─────────────────────────────────────────────────────
def createParamDecorator(extractor: Callable):
    """
    Create a custom param decorator.

    Example:
        CurrentUser = createParamDecorator(
            lambda data, request: request.state.user
        )

        @Get()
        def profile(self, user = CurrentUser()):
            return user

    The extractor receives (data, request) and returns the value.
    """
    def factory(data: Any = None, *, default: Any = ...):
        marker = _ParamMarker(ParamType.REQ)  # placeholder type
        marker._custom_extractor = extractor
        marker._custom_data = data
        marker._custom_default = default
        return marker
    return factory