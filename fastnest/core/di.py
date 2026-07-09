import inspect
from fastnest.core.decorators import get_meta
from fastnest.core.tokens import Inject


def _token_name(token):
    return token.__name__ if inspect.isclass(token) else repr(token)


class Container:


    def __init__(self, parent: "Container" = None):
        self.instances = {}
        self.exported: set = set()
        self.parent = parent
        self._globals: dict = {}


    def register_exported(self, cls):
        self.exported.add(cls)

    def register_global(self, cls, instance):
        self._globals[cls] = instance

    def register_value(self, token, value):
        """Bind a token directly to an already-built value (useValue)."""
        self.instances[token] = value
        return value

    def register_provider(self, provider: dict):
        """
        Register a custom, NestJS-style provider entry and return the
        resolved instance:

            {"provide": Token, "useValue": some_instance}
            {"provide": Token, "useFactory": some_callable, "inject": [Dep1, Dep2]}
            {"provide": Token, "useClass": ConcreteImpl}

        `Token` may be a class or a string/symbol-like token.
        """
        token = provider["provide"]

        if "useValue" in provider:
            instance = provider["useValue"]
        elif "useClass" in provider:
            instance = self._create_instance(provider["useClass"])
        elif "useFactory" in provider:
            factory = provider["useFactory"]
            deps = [self.get(dep_token) for dep_token in provider.get("inject", [])]
            instance = factory(*deps)
        else:
            raise ValueError(
                f"Custom provider for {_token_name(token)!s} must define "
                "one of useValue, useClass, or useFactory"
            )

        self.instances[token] = instance
        return instance

    def get(self, token):

        if token in self.instances:
            return self.instances[token]


        if self.parent is not None:
            try:
                return self.parent.get(token)
            except LookupError:
                # Bug fix 3: only swallow "not found" — let real errors (circular deps, etc.) propagate
                pass


        if token in self._globals:
            return self._globals[token]

        if not (inspect.isclass(token) and get_meta(token, "is_injectable")):
            raise LookupError(f"{_token_name(token)} is not provided in this module or its imports")

        instance = self._create_instance(token)
        self.instances[token] = instance
        return instance

    def _create_instance(self, cls):
        signature = inspect.signature(cls.__init__)
        params = signature.parameters
        deps = {}
        for name, param in params.items():
            if name == "self":
                continue
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue

            if isinstance(param.default, Inject):
                dep_token = param.default.token
            else:
                dep_token = param.annotation
                if dep_token == inspect.Parameter.empty:
                    raise Exception(f"Missing annotation for {name} in {cls.__name__}")

            deps[name] = self.get(dep_token)
        return cls(**deps)

    def import_from(self, other: "Container"):
        for cls in other.exported:
            if cls in other.instances:
                self.instances[cls] = other.instances[cls]

    def all_instances(self):
        seen = {}
        seen.update(self._globals)
        seen.update(self.instances)
        if self.parent:
            for k, v in self.parent.all_instances().items():
                seen.setdefault(k, v)
        return seen