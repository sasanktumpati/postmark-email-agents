import os

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    pass


class Settings:
    def __init__(self):
        self.app_name: str = os.getenv("APP_NAME", "Postmark Email Agents APIs")
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

    def validate_database_config(self) -> bool:
        try:
            self._validate_config()
            return True
        except ConfigurationError:
            return False

    @property
    def database_url(self) -> str:
        """Synchronous database URL for psycopg2"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def async_database_url(self) -> str:
        """Asynchronous database URL for asyncpg"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


try:
    settings = Settings()
except ConfigurationError as e:
    print(f"Configuration Error: {e}")
    print("Please check your environment variables and try again.")
    settings = None
