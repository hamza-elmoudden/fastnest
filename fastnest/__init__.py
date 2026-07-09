# fastnest/__init__.py
"""
🪺 FastNest — A progressive Python framework inspired by NestJS.
"""
__version__ = "0.2.0"

# ─── Core ───
from fastnest.core.factory import (
    create_app,
    add_global_guard, add_global_interceptor, add_global_pipe, add_global_filter,
)
from fastnest.core.decorators import (
    Module, Controller, Injectable, Global,
    Get, Post, Put, Delete, Patch,
    UsePipe, UseGuard, UseInterceptor, UseExceptionFilter,
)
from fastnest.core.params import Body, Query, Param, Headers, Req
from fastnest.core.middleware import NestMiddleware, MiddlewareConfig
from fastnest.core.reflector import Reflector
from fastnest.core.dynamic_module import DynamicModule
from fastnest.core.tokens import Inject

# ─── Common ───
from fastnest.common.interfaces import (
    PipeTransform, CanActivate, NestInterceptor, ExceptionFilter,
)
from fastnest.common.pipes import (
    ValidationPipe, ParseIntPipe, ParseBoolPipe, DefaultValuePipe,
)
from fastnest.common.lifecycle import (
    OnModuleInit, OnApplicationBootstrap, OnModuleDestroy,
)
from fastnest.common.decorators import (
    SetMetadata, Roles, Public, createParamDecorator,
)
from fastnest.common.logger import Logger
from fastnest.common.exceptions import (
    HttpException,
    BadRequestException, UnauthorizedException,
    ForbiddenException, NotFoundException, ConflictException,
    UnprocessableEntityException, InternalServerErrorException,
    ServiceUnavailableException,
)
from fastnest.common.guards.roles_guard import RolesGuard


__all__ = [
    "__version__",
    # Core
    "create_app", "add_global_guard", "add_global_interceptor", "add_global_pipe",
    "add_global_filter",
    "Module", "Controller", "Injectable", "Global",
    "Get", "Post", "Put", "Delete", "Patch",
    "Body", "Query", "Param", "Headers", "Req",
    "UsePipe", "UseGuard", "UseInterceptor", "UseExceptionFilter",
    "NestMiddleware", "MiddlewareConfig",
    "Reflector", "DynamicModule", "Inject",
    # Interfaces
    "PipeTransform", "CanActivate", "NestInterceptor", "ExceptionFilter",
    # Pipes
    "ValidationPipe", "ParseIntPipe", "ParseBoolPipe", "DefaultValuePipe",
    # Lifecycle
    "OnModuleInit", "OnApplicationBootstrap", "OnModuleDestroy",
    # Meta
    "SetMetadata", "Roles", "Public", "createParamDecorator",
    # Utils
    "Logger",
    # Exceptions
    "HttpException",
    "BadRequestException", "UnauthorizedException",
    "ForbiddenException", "NotFoundException", "ConflictException",
    "UnprocessableEntityException", "InternalServerErrorException",
    "ServiceUnavailableException",
    # Guards
    "RolesGuard",
]