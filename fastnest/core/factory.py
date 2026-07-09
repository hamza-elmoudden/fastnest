# fastnest/core/factory.py
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel
import inspect

from fastnest.core.metadata import get_meta
from fastnest.core.di import Container
from fastnest.core.signature_cache import get_cached_signature
from fastnest.core.signature_rewriter import (
    rewrite_handler_signature, _RESERVED_REQUEST_KEY,
)
from fastnest.core.async_utils import call_sync_or_async, _is_coroutine_function
from fastnest.core.middleware import MiddlewareConfig
from fastnest.core.dynamic_module import DynamicModule
from fastnest.common.base import SchemaAwarePipe
from fastnest.common.logger import Logger
from fastnest.core.websocket import register_gateway, get_gateway_route


# ══════════════════════════════════════════════════════
#  Global Guard/Pipe/Interceptor registry — scoped per app
# ══════════════════════════════════════════════════════
class GlobalRegistry:
    """Holds the global guards/interceptors/pipes/filters for a single create_app() build."""

    def __init__(self):
        self.guards: list = []
        self.interceptors: list = []
        self.pipes: list = []
        self.filters: list = []


# Staging area for add_global_guard()/add_global_interceptor()/add_global_pipe()
# calls made *before* create_app() runs (the documented usage pattern). Each
# create_app() call consumes whatever is staged here and then clears it, so
# registrations never leak forward into an unrelated, later create_app() call.
_pending_registry = GlobalRegistry()

# Set to the registry of the app currently being built by create_app(), so that
# add_global_*() calls made from within a module's configure() hook (or anywhere
# else during the build) land on that app's registry instead of the pending one.
_active_registry: ContextVar = ContextVar("_active_registry", default=None)


def _current_registry() -> GlobalRegistry:
    return _active_registry.get() or _pending_registry


def add_global_guard(*g):       _current_registry().guards.extend(g)
def add_global_interceptor(*i): _current_registry().interceptors.extend(i)
def add_global_pipe(*p):        _current_registry().pipes.extend(p)
def add_global_filter(*f):      _current_registry().filters.extend(f)


def _instantiate(x):
    return x() if inspect.isclass(x) else x


# ══════════════════════════════════════════════════════
#  Lifecycle Registry  (✅ حل ب: instance-level _seen)
# ══════════════════════════════════════════════════════
class _LifecycleRegistry:
    def __init__(self):
        self._seen = set()          # ✅ instance-level (فقط لكل create_app)
        self.init_targets = []
        self.bootstrap_targets = []
        self.destroy_targets = []

    def register(self, instance):
        if id(instance) in self._seen:
            return
        self._seen.add(id(instance))

        if hasattr(instance, "on_module_init"):
            self.init_targets.append(instance)
        if hasattr(instance, "on_application_bootstrap"):
            self.bootstrap_targets.append(instance)
        if hasattr(instance, "on_module_destroy"):
            self.destroy_targets.append(instance)

    async def run_init(self, logger):
        for inst in self.init_targets:
            logger.debug(f"on_module_init → {type(inst).__name__}")
            await call_sync_or_async(inst.on_module_init)

    async def run_bootstrap(self, logger):
        for inst in self.bootstrap_targets:
            logger.debug(f"on_application_bootstrap → {type(inst).__name__}")
            await call_sync_or_async(inst.on_application_bootstrap)

    async def run_destroy(self, logger):
        for inst in reversed(self.destroy_targets):
            try:
                logger.debug(f"on_module_destroy → {type(inst).__name__}")
                await call_sync_or_async(inst.on_module_destroy)
            except Exception as e:
                logger.error(f"Error in on_module_destroy: {e}")


# ══════════════════════════════════════════════════════
#  Controller route detection  (✅ حل د)
# ══════════════════════════════════════════════════════
def _iter_route_handlers(controller):
    """
    Find every bound route handler on a controller, including:
    - regular methods
    - staticmethod (descriptor)
    - classmethod (descriptor)
    - inherited methods from parent controllers
    """
    cls = type(controller)
    seen = set()

    for klass in cls.__mro__:
        if klass is object:
            continue
        for name, raw in klass.__dict__.items():
            if name in seen:
                continue

            # Detect the underlying function to check for _route_meta
            func = None
            if isinstance(raw, staticmethod):
                func = raw.__func__
            elif isinstance(raw, classmethod):
                func = raw.__func__
            elif inspect.isfunction(raw):
                func = raw

            if func is None or not hasattr(func, "_route_meta"):
                continue

            seen.add(name)
            # Get the bound version for calling
            bound = getattr(controller, name)
            yield name, bound, func


# ══════════════════════════════════════════════════════
#  Module Registration with DynamicModule support
# ══════════════════════════════════════════════════════
def _unwrap_module(module):
    """Resolve DynamicModule → (module_cls, dynamic_config)"""
    if isinstance(module, DynamicModule):
        return module.module, module
    return module, None


def _register_module(module_ref, app, root_container, lifecycle,
                     middleware_config, module_cache, logger, registry,
                     gateway_registry):

    module_cls, dynamic = _unwrap_module(module_ref)

    cache_key = dynamic if dynamic else module_cls
    if cache_key in module_cache:
        return module_cache[cache_key]

    module_container = Container(parent=root_container)
    module_cache[cache_key] = module_container

    # Merge static + dynamic metadata
    imports     = list(get_meta(module_cls, "imports", []))
    providers   = list(get_meta(module_cls, "providers", []))
    controllers = list(get_meta(module_cls, "controllers", []))
    exports     = list(get_meta(module_cls, "exports", []))
    is_global   = get_meta(module_cls, "is_global", False)

    if dynamic:
        imports     += dynamic.imports
        providers   += dynamic.providers
        controllers += dynamic.controllers
        exports     += dynamic.exports
        if dynamic.is_global is not None:
            is_global = dynamic.is_global

    logger.debug(f"Registering module: {module_cls.__name__}"
                 f"{' (dynamic)' if dynamic else ''}")

    # ─── imports first ───
    for imp in imports:
        imported_c = _register_module(
            imp, app, root_container, lifecycle,
            middleware_config, module_cache, logger, registry,
            gateway_registry,
        )
        module_container.import_from(imported_c)

    # ─── providers ───
    exports_set = set(exports)
    for prov in providers:
        if isinstance(prov, dict):
            # Custom provider: {"provide": Token, "useValue"/"useClass"/"useFactory": ...}
            token = prov["provide"]
            instance = module_container.register_provider(prov)
        else:
            token = prov
            instance = module_container.get(prov)
        lifecycle.register(instance)
        if token in exports_set:
            module_container.register_exported(token)
        if is_global:
            root_container.register_global(token, instance)

    # ─── configure middleware ───
    if hasattr(module_cls, "configure"):
        try:
            inst = module_cls()
        except TypeError:
            inst = module_cls
        inst.configure(middleware_config)

    # ─── WebSocket Gateways ────────────────────────────────
    gateways = list(get_meta(module_cls, "gateways", []))
    if hasattr(dynamic, "gateways") and dynamic:
        gateways += getattr(dynamic, "gateways", [])
    for gw_cls in gateways:
        path, namespace, mount_path = get_gateway_route(gw_cls)
        route_key = (path, namespace)
        existing = gateway_registry.get(route_key)
        if existing is not None and existing is not gw_cls:
            raise ValueError(
                f"WebSocket gateway route collision: {existing.__name__!r} and "
                f"{gw_cls.__name__!r} both resolve to path={path!r} "
                f"namespace={namespace!r} (mount_path={mount_path!r}). "
                f"Give one of them a distinct path or namespace."
            )
        gateway_registry[route_key] = gw_cls

        gw = module_container._create_instance(gw_cls)
        lifecycle.register(gw)
        register_gateway(gw, gw_cls, app, logger)

    # ─── controllers ───
    for ctrl_cls in controllers:
        ctrl = module_container._create_instance(ctrl_cls)
        lifecycle.register(ctrl)
        _register_controller_routes(ctrl, ctrl_cls, app, logger, registry)

    return module_container


# ══════════════════════════════════════════════════════
#  Routing
# ══════════════════════════════════════════════════════
def _is_pydantic_model(tp):
    try:
        return inspect.isclass(tp) and issubclass(tp, BaseModel)
    except TypeError:
        return False


def _build_param_type_map(handler):
    sig = get_cached_signature(handler)
    return {
        n: p.annotation for n, p in sig.parameters.items()
        if p.annotation is not inspect.Parameter.empty
    }


def _register_controller_routes(controller, ctrl_cls, app: FastAPI, logger, registry):
    prefix = get_meta(ctrl_cls, "prefix", "")

    for name, bound, func in _iter_route_handlers(controller):
        route = func._route_meta
        path = "/" + "/".join(p for p in [prefix, route["path"]] if p)

        new_sig, handler_params, req_alias = rewrite_handler_signature(bound)
        param_types = _build_param_type_map(bound)

        # Merge feature decorators (supports inheritance via get_meta)
        method_pipes = getattr(func, "_pipes", [])
        ctrl_pipes   = get_meta(ctrl_cls, "pipes", [])
        pipes        = registry.pipes + ctrl_pipes + method_pipes

        method_guards = getattr(func, "_guards", [])
        ctrl_guards   = get_meta(ctrl_cls, "guards", [])
        guards        = registry.guards + ctrl_guards + method_guards

        method_ics = getattr(func, "_interceptors", [])
        ctrl_ics   = get_meta(ctrl_cls, "interceptors", [])
        interceptors = registry.interceptors + ctrl_ics + method_ics

        method_filters = getattr(func, "_exception_filters", [])
        ctrl_filters   = get_meta(ctrl_cls, "exception_filters", [])
        filters        = registry.filters + ctrl_filters + method_filters

        endpoint = _build_endpoint(
            handler=bound, signature=new_sig,
            handler_params=handler_params, request_alias=req_alias,
            guards=guards, pipes=pipes,
            interceptors=interceptors, filters=filters,
            param_types=param_types, handler_func=func,
        )

        logger.debug(f"  → {route['method']:6s} {path}")
        app.add_api_route(path, endpoint, methods=[route["method"]])


def _build_endpoint(handler, signature, handler_params, request_alias,
                    guards, pipes, interceptors, filters,
                    param_types, handler_func):

    is_async = _is_coroutine_function(handler)
    pipe_instances = [_instantiate(p) for p in pipes]

    async def endpoint(**kwargs):
        # Bug fix 1: sentinel instead of `or` — avoids skipping falsy request values
        _SENTINEL = object()
        _r = kwargs.get(request_alias, _SENTINEL)
        request = _r if _r is not _SENTINEL else kwargs.get(_RESERVED_REQUEST_KEY)

        if request is None:
            raise HTTPException(status_code=500, detail="Request object could not be resolved")

        # Expose handler func to guards (for Reflector)
        request.state.handler = handler_func
        request.state.controller = type(handler.__self__) if hasattr(handler, "__self__") else None

        # Guards
        for g in guards:
            if not await call_sync_or_async(_instantiate(g).can_activate, request):
                raise HTTPException(status_code=403, detail="Forbidden")

        # Pipes
        for key in list(kwargs.keys()):
            if key in (_RESERVED_REQUEST_KEY, request_alias):
                continue
            value = kwargs[key]
            ptype = param_types.get(key)

            if _is_pydantic_model(ptype) and isinstance(value, dict):
                value = ptype(**value)

            for pipe in pipe_instances:
                if isinstance(pipe, SchemaAwarePipe) and pipe.schema is None:
                    pipe.schema = ptype if _is_pydantic_model(ptype) else None
                    try:
                        value = await call_sync_or_async(pipe.transform, value)
                    finally:
                        pipe.schema = None
                else:
                    value = await call_sync_or_async(pipe.transform, value)
            kwargs[key] = value

        # Interceptors: before
        ic_instances = [_instantiate(i) for i in interceptors]
        for i in ic_instances:
            await call_sync_or_async(i.intercept_before, request)

        call_kwargs = {k: v for k, v in kwargs.items() if k in handler_params}

        # Apply custom param extractors (createParamDecorator)
        _func = getattr(handler_func, "__func__", handler_func)
        extractors = getattr(_func, "_custom_extractors", {})
        for pname, (extractor, data) in extractors.items():
            call_kwargs[pname] = extractor(data, request)

        try:
            if is_async:
                response = await handler(**call_kwargs)
            else:
                response = handler(**call_kwargs)
                if inspect.isawaitable(response):
                    response = await response
        except HTTPException:
            raise
        except Exception as exc:
            # `filters` is assembled broad-to-narrow (global, controller, method) so it
            # reads naturally alongside guards/pipes/interceptors, but for *catching* we
            # want the opposite: a filter registered closer to the handler should be able
            # to override a broader one. So we walk it narrow-to-broad (method → controller
            # → global) and take the first filter that returns a non-None result.
            for fcls in reversed(filters):
                result = await call_sync_or_async(_instantiate(fcls).catch, exc, request)
                if result:
                    return JSONResponse(
                        status_code=result.get("statusCode", 500), content=result)
            raise

        for i in reversed(ic_instances):
            response = await call_sync_or_async(i.intercept_after, request, response)

        return response

    endpoint.__signature__ = signature
    endpoint.__name__ = handler.__name__
    return endpoint


# ══════════════════════════════════════════════════════
#  Middleware Bridge
# ══════════════════════════════════════════════════════
class _MiddlewareBridge(BaseHTTPMiddleware):
    def __init__(self, app, config: MiddlewareConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        matched = self.config.matches(request.url.path, request.method)
        if not matched:
            return await call_next(request)

        async def run_chain(i, req):
            if i >= len(matched):
                return await call_next(req)
            mw = _instantiate(matched[i])
            async def next_fn(r): return await run_chain(i + 1, r)
            return await call_sync_or_async(mw.use, req, next_fn)

        return await run_chain(0, request)


# ══════════════════════════════════════════════════════
#  create_app  (✅ حل أ: lifespan بدلاً من on_event)
# ══════════════════════════════════════════════════════
def create_app(module, *, debug: bool = False, title: str = "FastNest",
               guards: list = None, interceptors: list = None, pipes: list = None,
               filters: list = None) -> FastAPI:
    logger = Logger("FastNest")
    if debug:
        logger.set_level("DEBUG")

    root_container = Container()
    lifecycle = _LifecycleRegistry()
    middleware_config = MiddlewareConfig()
    module_cache: dict = {}
    gateway_registry: dict = {}

    # Build this app's own global registry: start from whatever was staged via
    # add_global_guard()/add_global_interceptor()/add_global_pipe() before this
    # call, plus anything passed explicitly, then clear the staging area so it
    # doesn't leak into the *next* create_app() call.
    registry = GlobalRegistry()
    registry.guards.extend(_pending_registry.guards)
    registry.interceptors.extend(_pending_registry.interceptors)
    registry.pipes.extend(_pending_registry.pipes)
    registry.filters.extend(_pending_registry.filters)
    registry.guards.extend(guards or [])
    registry.interceptors.extend(interceptors or [])
    registry.pipes.extend(pipes or [])
    registry.filters.extend(filters or [])

    _pending_registry.guards.clear()
    _pending_registry.interceptors.clear()
    _pending_registry.pipes.clear()
    _pending_registry.filters.clear()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info(f"🪺 Starting {title}...")
        await lifecycle.run_init(logger)
        await lifecycle.run_bootstrap(logger)
        logger.info("✅ Application ready")
        yield
        logger.info("🛑 Shutting down...")
        await lifecycle.run_destroy(logger)
        logger.info("👋 Goodbye")

    app = FastAPI(title=title, lifespan=lifespan, debug=debug)

    # While the module tree is being built, add_global_*() calls (e.g. from a
    # module's configure() hook) should land on THIS app's registry.
    token = _active_registry.set(registry)
    try:
        _register_module(module, app, root_container, lifecycle,
                         middleware_config, module_cache, logger, registry,
                         gateway_registry)
    finally:
        _active_registry.reset(token)

    if middleware_config._entries:
        app.add_middleware(_MiddlewareBridge, config=middleware_config)

    return app