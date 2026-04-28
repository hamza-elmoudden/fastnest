from fastnest.core.decorators import Controller, Delete, Get, Post, Put, UseGuard, UseInterceptor, UsePipe
from fastnest.core.params import Body, Param, Query
from fastnest.common.pipes import ValidationPipe

from example.posts.dto.update_post_dto import UpdatePostDto
from .posts_service import PostsService
from .dto.create_post_dto import CreatePostDto
from example.common.guards.jwt_guard import JwtGuard
from example.common.interceptors.logging_interceptor import LoggingInterceptor
from example.common.decorators.current_user_decorator import CurrentUser


@UseGuard(JwtGuard)
@UseInterceptor(LoggingInterceptor)
@Controller("posts")
class PostsController:
    def __init__(self, service: PostsService):
        self.service = service

    @Get("/")
    async def find_all(self, author_id: str = Query(default=None)):
        return await self.service.find_all(author_id)

    @Get("/{post_id}") 
    async def find_one(self, post_id: str = Param()):
        return await self.service.find_one(post_id)

    @Post("/")
    @UsePipe(ValidationPipe)
    async def create(self, body: CreatePostDto = Body(), me=CurrentUser()):
        return await self.service.create(body, me["sub"])

    @Put("/{post_id}") 
    @UsePipe(ValidationPipe)
    async def update(self, post_id: str = Param(), body: UpdatePostDto = Body(), me=CurrentUser()):
        return await self.service.update(post_id, body, me)

    @Delete("/{post_id}") # أضف /
    async def remove(self, post_id: str = Param(), me=CurrentUser()):
        return await self.service.remove(post_id, me)