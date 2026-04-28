import os
from fastapi import Request
from fastnest.common.interfaces import CanActivate
from fastnest.common.exceptions import UnauthorizedException
from example.utils.security import verify_jwt

class JwtGuard(CanActivate):
    def can_activate(self, request: Request) -> bool:
        secret = os.getenv("JWT_SECRET", "12WWWD44RGTY6HG55V435G40I")
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise UnauthorizedException("Missing Authorization header")
        payload = verify_jwt(auth.split(" ", 1)[-1].strip(), secret)
        if not payload:
            raise UnauthorizedException("Invalid or expired token")
        request.state.user = payload
        return True