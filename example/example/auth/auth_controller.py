from fastnest.core.decorators import Controller, Post, Get, UseInterceptor, UseGuard, UsePipe
from fastnest.core.params import Body
from fastnest.common.pipes import ValidationPipe
from .auth_service import AuthService
from .dto.register_dto import RegisterDto
from .dto.login_dto import LoginDto
from example.common.interceptors.logging_interceptor import LoggingInterceptor
from example.common.guards.jwt_guard import JwtGuard
from example.common.decorators.current_user_decorator import CurrentUser

@UseInterceptor(LoggingInterceptor)
@Controller("auth")
class AuthController:
    def __init__(self, service: AuthService):
        self.service = service

    @Post("register")
    @UsePipe(ValidationPipe)
    async def register(self, body: RegisterDto = Body()):
        return await self.service.register(body)

    @Post("login")
    @UsePipe(ValidationPipe)
    async def login(self, body: LoginDto = Body()):
        return await self.service.login(body)

    @Get("me")
    @UseGuard(JwtGuard)
    async def me(self, user=CurrentUser()):
        return await self.service.me(user["sub"])