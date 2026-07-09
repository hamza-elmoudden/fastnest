from fastnest.core.decorators import Controller, Get, Module

from .config.config_module import ConfigModule


@Controller()
class HealthController:
    @Get("/health")
    async def health(self):
        return {"status": "ok"}


@Module(
    imports=[
        ConfigModule.for_root(),
    ],
    controllers=[HealthController],
)
class AppModule:
    pass
