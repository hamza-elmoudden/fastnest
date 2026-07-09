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
    async def find_all(self, q: str = Query(default=None)):
        return self.service.find_all(q)

    @Get("/{${singular}_id}")
    async def find_one(self, ${singular}_id=Param("${singular}_id")):
        return self.service.find_one(int(${singular}_id))

    @Post("/")
    async def create(self, body: Create${SingularClass}Dto = Body()):
        return self.service.create(body)

    @Put("/{${singular}_id}")
    async def update(self, ${singular}_id=Param("${singular}_id"), body: Update${SingularClass}Dto = Body()):
        return self.service.update(int(${singular}_id), body)

    @Delete("/{${singular}_id}")
    async def remove(self, ${singular}_id=Param("${singular}_id")):
        return self.service.remove(int(${singular}_id))
