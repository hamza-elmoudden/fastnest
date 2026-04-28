import uuid
from typing import List, Optional
from fastnest.core.decorators import Injectable
from fastnest.common.exceptions import NotFoundException, ForbiddenException
from example.database.database_service import DatabaseService


@Injectable()
class PostsService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def create(self, data, author_id: int):
        query = "INSERT INTO posts (title, content, author_id) VALUES ($1, $2, $3) RETURNING *"
        row = await self.db.fetchrow(query, data.title, data.content, author_id)
        return dict(row)
    
    async def find_all(self, author_id: str = None):
        if author_id:
            rows = await self.db.fetch("SELECT * FROM posts WHERE author_id = $1", author_id)
        else:
            rows = await self.db.fetch("SELECT * FROM posts")
        return [dict(r) for r in rows]

    async def update(self, post_id: str, data, user_info: dict):
        post = await self.db.fetchrow("SELECT * FROM posts WHERE id = $1", post_id)
        if not post: raise NotFoundException()
        
        if str(post["author_id"]) != str(user_info["sub"]) and "admin" not in user_info["roles"]:
            raise ForbiddenException("Not your post")

        row = await self.db.fetchrow("UPDATE posts SET title=$1 WHERE id=$2 RETURNING *", data.title, post_id)
        return dict(row)

    async def remove(self, post_id: str, user_info: dict):
        post = await self.db.fetchrow("SELECT * FROM posts WHERE id = $1", post_id)
        if not post: raise NotFoundException()

        if str(post["author_id"]) != str(user_info["sub"]) and "admin" not in user_info["roles"]:
            raise ForbiddenException("Not your post")

        await self.db.execute("DELETE FROM posts WHERE id = $1", post_id)
        return {"message": "Post deleted"}