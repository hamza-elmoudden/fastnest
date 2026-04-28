from fastnest.core.decorators import Module
from .users_controller import UsersController
from .users_service import UsersService

@Module(controllers=[UsersController], providers=[UsersService])
class UsersModule:
    pass