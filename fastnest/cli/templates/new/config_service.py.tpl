from pydantic_settings import BaseSettings, SettingsConfigDict

from fastnest.core.decorators import Injectable


@Injectable()
class ConfigService(BaseSettings):
    """
    Reads config from a .env file (gitignored, see .env.example) or real
    process environment variables. Every field below has a safe default
    since a fresh project has no secrets yet.

    Once you add auth, a database, or anything else that needs a real
    secret, add required fields here WITHOUT a default (e.g. `db_url: str`)
    so pydantic-settings fails fast at startup instead of silently running
    with a hardcoded value — see example/example/config/config_service.py
    in the FastNest repo for a fuller, secret-requiring reference.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "my-app"
    debug: bool = False

    def __init__(self) -> None:
        # See the reference ConfigService for why this stays a plain
        # no-arg __init__ instead of BaseSettings' generated signature.
        super().__init__()

    def get(self, key: str):
        """Backward-compatible dict-style accessor for existing call sites."""
        return getattr(self, key)
