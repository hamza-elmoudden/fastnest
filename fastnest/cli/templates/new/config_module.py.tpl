from fastnest.core.decorators import Module
from fastnest.core.dynamic_module import DynamicModule

from .config_service import ConfigService


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
