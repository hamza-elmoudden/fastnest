from fastnest.core.decorators import Injectable
from fastnest.common.exceptions import NotFoundException

# In-memory storage — good for prototyping a resource end to end.
#
# To back this with a real database instead, inject a DatabaseService
# (see example/example/database/database_service.py) and swap the list
# operations below for queries, e.g.:
#
#     def __init__(self, db: DatabaseService):
#         self.db = db


@Injectable()
class ${ClassName}Service:
    def __init__(self):
        self._items: list = []

    def find_all(self, q: str = None):
        if q:
            return [i for i in self._items if q.lower() in str(i.get("name", "")).lower()]
        return self._items

    def find_one(self, ${singular}_id: int):
        for item in self._items:
            if item["id"] == ${singular}_id:
                return item
        raise NotFoundException(f"${SingularClass} #{${singular}_id} not found")

    def create(self, dto):
        item = {"id": len(self._items) + 1, **dto.model_dump()}
        self._items.append(item)
        return item

    def update(self, ${singular}_id: int, dto):
        item = self.find_one(${singular}_id)
        item.update(dto.model_dump())
        return item

    def remove(self, ${singular}_id: int):
        item = self.find_one(${singular}_id)
        self._items.remove(item)
        return {"deleted": ${singular}_id}
