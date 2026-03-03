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

    DATABASE_URL: str = "postgresql://localhost:5432/securescan"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    WORKSPACE_DIR: str = "./workspace"
    PROJECT_ROOT: str = "/tmp/securescan/projects"
    SEMGREP_ENABLED: bool = True
    NPM_AUDIT_ENABLED: bool = True
    TRUFFLEHOG_ENABLED: bool = True


settings = Settings()
