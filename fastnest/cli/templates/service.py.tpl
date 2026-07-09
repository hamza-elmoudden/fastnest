from fastnest.core.decorators import Injectable


@Injectable()
class ${ClassName}Service:
    def __init__(self):
        pass

    async def find_all(self, page: int = 1, limit: int = 10):
        # TODO: implement find_all
        pass

    async def find_one(self, id: str):
        # TODO: implement find_one
        pass

    async def create(self, dto):
        # TODO: implement create
        pass

    async def update(self, id: str, dto):
        # TODO: implement update
        pass

    async def remove(self, id: str):
        # TODO: implement remove
        pass
