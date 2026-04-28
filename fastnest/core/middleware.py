from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Union, List, Pattern
from fastapi import Request, Response
import re
import inspect


class NestMiddleware(ABC):
    
    @abstractmethod
    def use(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Union[Response, Awaitable[Response]]:
        ...


class MiddlewareConfig:

    def __init__(self):
        # list[ (middleware_cls_or_instance, [compiled_patterns], [methods]) ]
        self._entries: List[tuple] = []

    def apply(self, *middlewares):
        """
        middleware_config.apply(AuthMiddleware).for_routes("/users/*")
        """
        return _MiddlewareBuilder(self, list(middlewares))

    def _add(self, middlewares, patterns, methods):
        for mw in middlewares:
            self._entries.append((mw, patterns, methods))

    def matches(self, path: str, method: str):
        matched = []
        for mw, patterns, methods in self._entries:
            if methods and method.upper() not in methods:
                continue
            if not patterns:
                matched.append(mw)
                continue
            if any(p.match(path) for p in patterns):
                matched.append(mw)
        return matched


class _MiddlewareBuilder:

    def __init__(self, config: MiddlewareConfig, middlewares):
        self._config = config
        self._middlewares = middlewares

    def for_routes(self, *routes: str, methods=None):
        """
        for_routes("/users", "/posts/*")
        for_routes("/admin/*", methods=["GET", "POST"])
        """
        patterns = [self._compile_route(r) for r in routes]
        method_set = {m.upper() for m in methods} if methods else set()
        self._config._add(self._middlewares, patterns, method_set)
        return self

    def for_all(self, methods=None):
        method_set = {m.upper() for m in methods} if methods else set()
        self._config._add(self._middlewares, [], method_set)
        return self

    @staticmethod
    def _compile_route(route: str) -> Pattern:
        # Escape the route, then convert wildcards:
        #   {param} -> matches one non-slash segment
        #   *       -> matches one non-slash segment (not greedy across /)
        pattern = re.escape(route)
        pattern = re.sub(r"\\\{[^}]+\\\}", r"[^/]+", pattern)  # {id} -> [^/]+
        pattern = pattern.replace(r"\*", "[^/]+")                  # *    -> [^/]+
        return re.compile(f"^{pattern}$")