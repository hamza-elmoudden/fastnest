from fastnest.core.decorators import Module
from .database_service import DatabaseService

@Module(providers=[DatabaseService], exports=[DatabaseService])
class DatabaseModule:
    pass