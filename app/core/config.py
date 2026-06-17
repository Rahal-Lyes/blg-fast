from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # Database
    # DATABASE_URL: str = "postgresql://app_user:app_password@localhost:5432/app_db"
    DATABASE_URL="postgresql://baligh_user:W0k2zVg4NoOQc81IPtJLPZN0Za3N2tWE@dpg-d8p51677fcjvv50-a:5432/baligh_db"

    # JWT
    SECRET_KEY: str = "change_this_to_a_long_random_secret_key_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Admin
    ADMIN_PASSWORD: str = "admin123"

    # Upload
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGES_PER_REPORT: int = 6

    # App
    APP_ENV: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8080","https://blg-fast.onrender.com"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
