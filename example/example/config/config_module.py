from fastnest.core.decorators import Module
from fastnest.core.dynamic_module import DynamicModule
from .config_service import ConfigService

# ConfigService (a pydantic-settings BaseSettings) requires DB_URL and
# JWT_SECRET to be set via a real .env file (gitignored — copy .env.example
# to .env and fill in real values) or real process environment variables.
# There are no hardcoded fallbacks: if either is missing, the app fails to
# start with a clear pydantic ValidationError instead of running with a
# weak, publicly-visible default secret.
@Module(providers=[], exports=[])
class ConfigModule:
    @classmethod
    def for_root(cls):
        return DynamicModule(
            module=cls,
            providers=[ConfigService],
            exports=[ConfigService],
            is_global=True,
        )