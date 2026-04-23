"""
Application Configuration

Loads environment variables and provides typed settings
for database, AI model, and external API configurations.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_ENV: str = "development"
    DEBUG: bool = True

    # --- Firebase ---
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CREDENTIALS_PATH: str = "firebase-service-account.json"
    FIREBASE_STORAGE_BUCKET: str = ""

    # --- AI Model (GLM) ---
    GLM_API_KEY: str = ""
    GLM_API_BASE_URL: str = ""
    GLM_MODEL_NAME: str = "glm-4"
    GLM_MAX_TOKENS: int = 4096

    # --- Google APIs ---
    GOOGLE_PLACES_API_KEY: str = ""
    GOOGLE_MAPS_API_KEY: str = ""
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""

    # --- Auth ---
    # Using Firebase Auth — no custom JWT needed
    # JWT_SECRET_KEY is only needed if you add a custom token layer
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS ---
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
