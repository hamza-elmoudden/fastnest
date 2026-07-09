from pydantic_settings import BaseSettings, SettingsConfigDict

from fastnest.core.decorators import Injectable


@Injectable()
class ConfigService(BaseSettings):
    """
    Reads required config from a .env file (gitignored, see .env.example)
    or real process environment variables. No defaults are provided for
    secrets — if DB_URL or JWT_SECRET are missing, pydantic-settings raises
    a ValidationError at construction time instead of silently falling back
    to a hardcoded value.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_url: str
    jwt_secret: str

    def __init__(self) -> None:
        # BaseSettings.__init__ takes **kwargs behind a `__pydantic_self__`
        # first parameter (not `self`), which the DI container's reflection
        # in Container._create_instance() doesn't recognize as skippable.
        # A plain no-arg __init__ keeps `cls()` construction working through
        # the container while still loading values from the environment/.env.
        super().__init__()

    def get(self, key: str):
        """Backward-compatible dict-style accessor for existing call sites."""
        return getattr(self, key)
