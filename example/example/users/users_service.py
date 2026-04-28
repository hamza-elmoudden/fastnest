import uuid
from typing import List, Optional
from fastnest.core.decorators import Injectable
from fastnest.common.logger import Logger
from fastnest.common.exceptions import InternalServerErrorException, NotFoundException, ConflictException, BadRequestException, ForbiddenException
from example.database.database_service import DatabaseService
from example.utils.security import hash_password


@Injectable()
class UsersService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def create(self, data):
        hashed = hash_password(data.password)
        query = "INSERT INTO users (name, email, password_hash, roles) VALUES ($1, $2, $3, $4) RETURNING id, name, email, roles"
        row = await self.db.fetchrow(query, data.name, data.email, hashed, data.roles)
        return dict(row)

    async def find_all(self, page: int = 1, limit: int = 10) -> dict:
        offset = (page - 1) * limit
        rows = await self.db.fetch(
            """
            SELECT id, name, email, roles, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset
        )
        total = await self.db.fetchrow("SELECT COUNT(*) AS c FROM users")
        return {
            "data":  rows,
            "total": total["c"],
            "page":  page,
            "limit": limit,
        }

    async def find_by_role(self, role: str):
        rows = await self.db.fetch("SELECT id, name, email, roles FROM users WHERE $1 = ANY(roles)", role)
        return [dict(r) for r in rows]

    async def find_one(self, user_id: str):
        row = await self.db.fetchrow("SELECT id, name, email, roles FROM users WHERE id = $1", user_id)
        if not row: raise NotFoundException("User not found")
        return dict(row)

    async def check_role(self, user_id: str, role: str):
        user = await self.find_one(user_id) 
        return {
            "has_role": role in user["roles"],
            "all_roles": user["roles"]
        }

    async def update(self, user_id: str, data):
        query = "UPDATE users SET name = $1 WHERE id = $2 RETURNING id, name, email, roles"
        row = await self.db.fetchrow(query, data.name, user_id)
        if not row: raise NotFoundException()
        return dict(row)

    async def update_roles(self, user_id: str, roles: list):
        query = "UPDATE users SET roles = $1 WHERE id = $2 RETURNING id, name, email, roles"
        row = await self.db.fetchrow(query, roles, user_id)
        if not row: raise NotFoundException()
        return dict(row)

    async def remove(self, user_id: str, admin_id: str):
        if str(user_id) == str(admin_id): 
            raise InternalServerErrorException("Cannot delete yourself")
        await self.db.execute("DELETE FROM users WHERE id = $1", user_id)
        return {"message": "User deleted"}