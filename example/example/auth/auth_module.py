from fastnest.core.decorators import Module
from .auth_controller import AuthController
from .auth_service import AuthService

@Module(controllers=[AuthController], providers=[AuthService])
class AuthModule:
    pass