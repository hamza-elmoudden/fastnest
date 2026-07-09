from fastnest.core.decorators import Injectable
from fastnest.common.logger import Logger
from fastnest.common.exceptions import ConflictException, UnauthorizedException, NotFoundException
import uuid
from example.database.database_service import DatabaseService
from example.config.config_service import ConfigService
from example.utils.security import hash_password, sign_jwt, verify_password
from .dto.register_dto import RegisterDto
from .dto.login_dto import LoginDto

@Injectable()
class AuthService:
    def __init__(self, db: DatabaseService, config: ConfigService):
        self.db = db
        self.config = config
        self.logger = Logger("AuthService")

    async def register(self, dto: RegisterDto) -> dict:
        existing = await self.db.fetchrow("SELECT id FROM users WHERE email = $1", dto.email)
        if existing:
            raise ConflictException(f"Email '{dto.email}' already registered")
        password_hash, password_salt = hash_password(dto.password)
        user = await self.db.fetchrow(
            "INSERT INTO users (name, email, password_hash, password_salt, roles) VALUES ($1, $2, $3, $4, $5) RETURNING id, name, email, roles, created_at",
            dto.name, dto.email, password_hash, password_salt, ["user"]
        )
        return dict(user)

    async def login(self, dto: LoginDto) -> dict:
        user = await self.db.fetchrow("SELECT * FROM users WHERE email = $1 AND is_active = TRUE", dto.email)
        if not user or not verify_password(dto.password, user["password_hash"], user["password_salt"]):
            raise UnauthorizedException("Invalid credentials")
        payload = {"sub": str(user["id"]), "email": user["email"], "name": user["name"], "roles": [str(r) for r in user["roles"]]}
        token = sign_jwt(payload, self.config.get("jwt_secret"))
        return {"access_token": token, "token_type": "bearer"}

    async def me(self, user_id: str) -> dict:
        user = await self.db.fetchrow("SELECT id, name, email, roles, created_at FROM users WHERE id = $1", uuid.UUID(user_id))
        if not user: raise NotFoundException("User not found")
        return dict(user)