from abc import ABC, abstractmethod
from typing import Union, Awaitable, Any


class PipeTransform(ABC):
    @abstractmethod
    def transform(self, value) -> Union[Any, Awaitable[Any]]:
        ...


class CanActivate(ABC):
    @abstractmethod
    def can_activate(self, request) -> Union[bool, Awaitable[bool]]:
        ...


class NestInterceptor(ABC):
    @abstractmethod
    def intercept_before(self, request) -> Union[None, Awaitable[None]]:
        ...

    @abstractmethod
    def intercept_after(self, request, response) -> Union[Any, Awaitable[Any]]:
        ...


class ExceptionFilter(ABC):
    @abstractmethod
    def catch(self, exception: Exception, request) -> Union[dict, Awaitable[dict]]:
        ...