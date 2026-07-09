from fastapi import Request
from fastnest.common.interfaces import CanActivate
from fastnest.common.exceptions import UnauthorizedException
from example.config.config_service import ConfigService
from example.utils.security import verify_jwt

# Guards are instantiated with no constructor args (not through the DI
# container), so ConfigService is built directly here rather than injected.
# This also means a missing JWT_SECRET fails loudly at import time (app
# startup) instead of falling back to a hardcoded secret.
_config = ConfigService()


class JwtGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise UnauthorizedException("Missing Authorization header")
        payload = verify_jwt(auth.split(" ", 1)[-1].strip(), _config.jwt_secret)
        if not payload:
            raise UnauthorizedException("Invalid or expired token")
        request.state.user = payload
        return True