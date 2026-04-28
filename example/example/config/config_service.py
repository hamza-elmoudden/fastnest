import os
from fastnest.core.decorators import Injectable

@Injectable()
class ConfigService:
    def __init__(self):
        self._cfg = {
            "db_url": os.getenv("DB_URL", "postgresql://postgres:123456789@localhost/fastnest_db"),
            "jwt_secret": os.getenv("JWT_SECRET", "12WWWD44RGTY6HG55V435G40I"),
        }

    def get(self, key: str):
        return self._cfg[key]