import os

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    pass


class Settings:
    def __init__(self):
        self.app_name: str = os.getenv("APP_NAME", "Actionable Mail APIs")
        self.app_version: str = os.getenv("APP_VERSION", "0.0.1")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"

        # Database configuration
        self.postgres_user: str = os.getenv("POSTGRES_USER")
        self.postgres_password: str = os.getenv("POSTGRES_PASSWORD")
        self.postgres_host: str = os.getenv("POSTGRES_HOST")
        self.postgres_port: str = os.getenv("POSTGRES_PORT")
        self.postgres_db: str = os.getenv("POSTGRES_DB")

        # Database pool configuration
        self.db_pool_size: int = int(os.getenv("DB_POOL_SIZE", "20"))
        self.db_max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "0"))
        self.db_pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.db_pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        self.sql_echo: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

        # Gemini API configuration
        self._gemini_api_key: str = os.getenv("GEMINI_API_KEY")
        self.gemini_model_name: str = os.getenv(
            "GEMINI_MODEL", "gemini-2.5-flash-preview-04-17"
        )

        # Postmark API configuration
        self._postmark_api_key: str = os.getenv("POSTMARK_API_KEY")

        self._secret_key: str = os.getenv("SECRET_KEY")
        self.api_key_salt: str = os.getenv("API_KEY_SALT", "API_KEY_SALT")

        self._validate_config()

    def _validate_config(self) -> None:
        missing_vars = []

        required_db_vars = {
            "POSTGRES_USER": self.postgres_user,
            "POSTGRES_PASSWORD": self.postgres_password,
            "POSTGRES_HOST": self.postgres_host,
            "POSTGRES_PORT": self.postgres_port,
            "POSTGRES_DB": self.postgres_db,
        }

        for var_name, var_value in required_db_vars.items():
            if not var_value:
                missing_vars.append(var_name)

        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        try:
            int(self.postgres_port)
        except (ValueError, TypeError):
            raise ConfigurationError(
                f"POSTGRES_PORT must be a valid number, got: {self.postgres_port}"
            )

        if self.db_pool_size <= 0:
            raise ConfigurationError("DB_POOL_SIZE must be greater than 0")

        if self.db_max_overflow < 0:
            raise ConfigurationError("DB_MAX_OVERFLOW must be non-negative")

        if self._gemini_api_key is None:
            raise ConfigurationError("GEMINI_API_KEY is not set")

        if self._postmark_api_key is None:
            raise ConfigurationError("POSTMARK_API_KEY is not set")

        if self._secret_key is None:
            raise ConfigurationError("SECRET_KEY is not set")

    def validate_database_config(self) -> bool:
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False

    def validate_gemini_api_key(self) -> bool:
        if not self._gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is not set")
        return True

    def validate_postmark_api_key(self) -> bool:
        if not self._postmark_api_key:
            raise ConfigurationError("POSTMARK_API_KEY is not set")
        return True

    @property
    def gemini_model(self) -> str:
        return f"google-gla:{self.gemini_model_name}"

    @property
    def gemini_api_key(self) -> str:
        self.validate_gemini_api_key()
        return self._gemini_api_key

    @property
    def database_url(self) -> str:
        """Synchronous database URL for psycopg2"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL for asyncpg"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def postmark_api_key(self) -> str:
        self.validate_postmark_api_key()
        return self._postmark_api_key

    @property
    def secret_key(self) -> str:
        return self._secret_key


def get_config() -> Settings:
    """Get the global configuration settings."""
    if settings is None:
        raise ConfigurationError("Configuration is not properly initialized")
    return settings


try:
    settings = Settings()
except ConfigurationError as e:
    print(f"Configuration Error: {e}")
    print("Please check your environment variables and try again.")
    settings = None


if settings:
    print(f"Debug mode is {'on' if settings.debug else 'off'}")
