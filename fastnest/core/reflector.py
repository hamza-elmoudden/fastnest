from typing import Any, Optional
from fastnest.core.metadata import get_meta


class Reflector:
    """
    Read custom metadata set by @SetMetadata or custom decorators.
    Used primarily inside Guards to implement role-based access control.
    """

    def get(self, key: str, target: Any, default: Any = None) -> Any:
        return get_meta(target, key, default)

    def get_all(self, key: str, targets: list, default: Any = None) -> list:
        """Collect metadata from multiple targets (method + controller)."""
        results = []
        for t in targets:
            v = self.get(key, t)
            if v is not None:
                if isinstance(v, list):
                    results.extend(v)
                else:
                    results.append(v)
        return results or default or []

    def get_all_and_override(self, key: str, targets: list,
                              default: Any = None) -> Optional[Any]:
        """Method-level overrides controller-level (first non-None wins)."""
        for t in targets:
            v = self.get(key, t)
            if v is not None:
                return v
        return default

    def get_all_and_merge(self, key: str, targets: list) -> list:
        """Merge list metadata from all targets."""
        merged = []
        for t in targets:
            v = self.get(key, t, [])
            if isinstance(v, list):
                merged.extend(v)
        return merged