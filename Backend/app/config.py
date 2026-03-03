"""Configuration (variables d'environnement)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    PROJECT_NAME: str = "SecureScan"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://localhost/securescan"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    WORKSPACE_DIR: str = "./workspace"

    # Auth JWT (cookie HTTP-only) — SECRET_KEY doit venir de .env en prod
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_COOKIE_NAME: str = "access_token"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 h
    COOKIE_SAMESITE: str = "lax"
    COOKIE_SECURE: bool = False  # True en HTTPS


settings = Settings()
