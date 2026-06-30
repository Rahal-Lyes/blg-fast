from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    # ── DATABASE ─────────────────────────────
    DATABASE_URL: str

    # ── JWT ──────────────────────────────────
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── ADMIN ────────────────────────────────
    ADMIN_PASSWORD: str

    # ── FILES ────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGES_PER_REPORT: int = 6

    # ── ENV ──────────────────────────────────
    APP_ENV: str = "development"

    # ── CORS ────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:19006",  # Expo important
        "https://blg-fast.onrender.com",
        "https://balighplus.onrender.com",

    ]

    # ── IMPORTANT DOCKER FIX ─────────────────
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()