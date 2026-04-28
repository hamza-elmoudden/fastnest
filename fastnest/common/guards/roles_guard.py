# fastnest/common/guards/roles_guard.py
from fastnest.common.interfaces import CanActivate
from fastnest.core.reflector import Reflector


class RolesGuard(CanActivate):
    """
    Reads @Roles('admin', ...) metadata and checks request.state.user.roles.
    """
    reflector = Reflector()

    def can_activate(self, request) -> bool:
        # Method + Controller level
        handler = getattr(request.state, "handler", None)
        controller = getattr(request.state, "controller", None)

        required = self.reflector.get_all_and_override(
            "roles", [handler, controller], default=None,
        )
        if required is None:
            return True  # No @Roles → public

        user = getattr(request.state, "user", None)
        if not user:
            return False

        if isinstance(user, dict):
            user_roles = user.get("roles", [])
        else:
            user_roles = getattr(user, "roles", []) or []
        return any(r in user_roles for r in required)