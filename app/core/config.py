"""Application settings, loaded from environment variables / .env file."""
from functools import lru_cache

from pydantic import EmailStr, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "GreenNest API"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # JWT
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CORS_ORIGINS: list[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]

    # Optional first-admin seed
    ADMIN_NAME: str | None = Field(default=None, min_length=2, max_length=100)
    ADMIN_EMAIL: EmailStr | None = None
    ADMIN_PASSWORD: str | None = Field(default=None, min_length=12)

    @field_validator("ADMIN_NAME", mode="before")
    @classmethod
    def trim_admin_name(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()