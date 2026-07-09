from fastnest.core.decorators import Controller, Get, Post, Put, Delete
from fastnest.core.params import Body, Param, Query
from .${name}_service import ${ClassName}Service
from .dto.create_${singular}_dto import Create${SingularClass}Dto
from .dto.update_${singular}_dto import Update${SingularClass}Dto


@Controller("${name}")
class ${ClassName}Controller:
    def __init__(self, service: ${ClassName}Service):
        self.service = service

    @Get("/")
    async def find_all(self, page: int = Query(default=1), limit: int = Query(default=10)):
        # TODO: implement find_all
        pass

    @Get("/{id}")
    async def find_one(self, id: str = Param()):
        # TODO: implement find_one
        pass

    @Post("/")
    async def create(self, body: Create${SingularClass}Dto = Body()):
        # TODO: implement create
        pass

    @Put("/{id}")
    async def update(self, id: str = Param(), body: Update${SingularClass}Dto = Body()):
        # TODO: implement update
        pass

    @Delete("/{id}")
    async def remove(self, id: str = Param()):
        # TODO: implement remove
        pass
