# fastnest/core/decorators.py
from fastnest.core.metadata import set_meta, get_meta   # re-export


def Module(
    imports: list = None,
    controllers: list = None,
    providers: list = None,
    exports: list = None,
    gateways: list = None,
):
    def decorator(cls):
        set_meta(cls, "imports",     imports or [])
        set_meta(cls, "controllers", controllers or [])
        set_meta(cls, "providers",   providers or [])
        set_meta(cls, "exports",     exports or [])
        set_meta(cls, "gateways",    gateways or [])
        set_meta(cls, "is_module",   True)
        return cls
    return decorator


def Global():
    def decorator(cls):
        set_meta(cls, "is_global", True)
        return cls
    return decorator


def Controller(prefix: str = ""):
    def decorator(cls):
        set_meta(cls, "prefix", prefix.strip("/"))
        set_meta(cls, "is_controller", True)
        return cls
    return decorator


def Injectable():
    def decorator(cls):
        set_meta(cls, "is_injectable", True)
        return cls
    return decorator


# ─── HTTP Methods ───
def _http(method: str):
    def wrap(path: str = ""):
        def decorator(func):
            func._route_meta = {"method": method, "path": path.strip("/")}
            return func
        return decorator
    return wrap


Get    = _http("GET")
Post   = _http("POST")
Put    = _http("PUT")
Delete = _http("DELETE")
Patch  = _http("PATCH")


# ─── Feature Decorators (method-level stored on function) ───
def _make_use(attr):
    def decorator(*items):
        def wrapper(target):
            if isinstance(target, type):
                # Class-level: read and write via metadata system
                existing = get_meta(target, attr, [])
                set_meta(target, attr, list(existing) + list(items))
            else:
                # Method-level: read and write via function attribute
                existing = getattr(target, f"_{attr}", [])
                setattr(target, f"_{attr}", list(existing) + list(items))
            return target
        return wrapper
    return decorator


UseGuard           = _make_use("guards")
UsePipe            = _make_use("pipes")
UseInterceptor     = _make_use("interceptors")
UseExceptionFilter = _make_use("exception_filters")