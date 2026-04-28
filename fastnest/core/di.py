import inspect
from fastnest.core.decorators import get_meta


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

    def get(self, cls):
       
        if cls in self.instances:
            return self.instances[cls]

        
        if self.parent is not None:
            try:
                return self.parent.get(cls)
            except LookupError:
                # Bug fix 3: only swallow "not found" — let real errors (circular deps, etc.) propagate
                pass

        
        if cls in self._globals:
            return self._globals[cls]

        if not get_meta(cls, "is_injectable"):
            raise LookupError(f"{cls.__name__} is not provided in this module or its imports")

        instance = self._create_instance(cls)
        self.instances[cls] = instance
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
            dep_class = param.annotation
            if dep_class == inspect.Parameter.empty:
                raise Exception(f"Missing annotation for {name} in {cls.__name__}")
            deps[name] = self.get(dep_class)
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