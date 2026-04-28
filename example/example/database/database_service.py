import asyncpg
from typing import Optional, List
from fastnest.core.decorators import Injectable
from fastnest.common.lifecycle import OnModuleInit, OnModuleDestroy
from fastnest.common.logger import Logger
from example.config.config_service import ConfigService

@Injectable()
class DatabaseService(OnModuleInit, OnModuleDestroy):
    def __init__(self, config: ConfigService):
        self.config = config
        self.logger = Logger("DatabaseService")
        self._pool: Optional[asyncpg.Pool] = None

    async def on_module_init(self):
        self.logger.info("Connecting to PostgreSQL...")
        self._pool = await asyncpg.create_pool(
            self.config.get("db_url"),
            min_size=2,
            max_size=10,
        )
        self.logger.info("PostgreSQL pool ready")

    async def on_module_destroy(self):
        if self._pool:
            await self._pool.close()
            self.logger.info("PostgreSQL pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database not connected")
        return self._pool

    async def fetch(self, query: str, *args) -> List[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]

    async def fetchrow(self, query: str, *args) -> Optional[dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None

    async def execute(self, query: str, *args) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)