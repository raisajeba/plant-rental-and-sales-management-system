"""Application settings, loaded from environment variables / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "GreenNest API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str | None = None
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "greennest"
    DB_USER: str = "greennest_user"
    DB_PASSWORD: str

    # JWT
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]

    # Optional first-admin seed
    ADMIN_NAME: str | None = None
    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    # SSLCommerz
    SSLCOMMERZ_STORE_ID: str
    SSLCOMMERZ_STORE_PASSWORD: str
    SSLCOMMERZ_IS_SANDBOX: bool = True
    PUBLIC_BASE_URL: str | None = None
    FRONTEND_BASE_URL: str | None = "http://localhost:5500/frontend"  # /frontend path ti add kore din

    @property
    def sync_database_url(self) -> str:
        """DATABASE_URL থাকলে সেটি নেবে, না থাকলে MySQL URL তৈরি করবে।"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()