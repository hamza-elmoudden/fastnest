from abc import ABC, abstractmethod
from typing import Union, Awaitable


class OnModuleInit(ABC):
    
    @abstractmethod
    def on_module_init(self) -> Union[None, Awaitable[None]]:
        ...


class OnApplicationBootstrap(ABC):
    
    @abstractmethod
    def on_application_bootstrap(self) -> Union[None, Awaitable[None]]:
        ...


class OnModuleDestroy(ABC):
   
    @abstractmethod
    def on_module_destroy(self) -> Union[None, Awaitable[None]]:
        ...