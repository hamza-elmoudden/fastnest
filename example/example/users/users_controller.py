from fastnest.core.decorators import Controller, Get, Patch, Post, Put, Delete, UseGuard, UseInterceptor, UsePipe
from fastnest.core.params import Body, Param, Query
from fastnest.common.pipes import ValidationPipe
from fastnest.common.guards.roles_guard import RolesGuard
from fastnest.common.decorators import Roles
from .users_service import UsersService
from .dto.create_user_dto import CreateUserDto
from .dto.update_user_dto import UpdateUserDto
from example.common.guards.jwt_guard import JwtGuard
from example.common.interceptors.logging_interceptor import LoggingInterceptor
from example.common.decorators.current_user_decorator import CurrentUser

@UseGuard(JwtGuard)
@UseInterceptor(LoggingInterceptor)
@Controller("users")
class UsersController:
    def __init__(self, service: UsersService):
        self.service = service

    @Get("/")
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def find_all(self, page: int = Query(default=1), limit: int = Query(default=10)):
        return await self.service.find_all(page, limit)


    @Get("/by-role") 
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def find_by_role(self, role: str = Query()):
        return await self.service.find_by_role(role)

    @Get("/{user_id}")
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def find_one(self, user_id: str = Param()):
        return await self.service.find_one(user_id)


    @Get("/{user_id}/check-role")
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def check_role(self, user_id: str = Param(), role: str = Query()):
        return await self.service.check_role(user_id, role)
    

    @Post("/")
    @Roles("admin")
    @UseGuard(RolesGuard)
    @UsePipe(ValidationPipe)
    async def create(self, body: CreateUserDto = Body()):
        return await self.service.create(body)


    @Put("/{user_id}")
    @Roles("admin")
    @UseGuard(RolesGuard)
    @UsePipe(ValidationPipe)
    async def update(self, user_id: str = Param(), body: UpdateUserDto = Body()):
        return await self.service.update(user_id, body)


    @Patch("/{user_id}/roles") 
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def update_roles(self, user_id: str = Param(), body: dict = Body()):
        roles = body.get("roles")
        return await self.service.update_roles(user_id, roles)
    


    @Delete("{user_id}")
    @Roles("admin")
    @UseGuard(RolesGuard)
    async def remove(self, user_id: str = Param(), me=CurrentUser()):
        return await self.service.remove(user_id, me["sub"])