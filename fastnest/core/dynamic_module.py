from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DynamicModule:
    """
    Returned by Module.for_root() / Module.for_feature() etc.
    Adds runtime-configured providers/imports/exports to the static @Module.
    """
    module: type
    imports: List = field(default_factory=list)
    providers: List = field(default_factory=list)
    controllers: List = field(default_factory=list)
    exports: List = field(default_factory=list)
    is_global: Optional[bool] = None

    # ─── Helpers ───
    def __hash__(self):
        return id(self)