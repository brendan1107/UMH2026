"""
Application Configuration

Loads environment variables and provides typed settings
for database, AI model, and external API configurations.
"""

# What is config.py for?
# The config.py file is responsible for loading environment variables and providing a structured, typed configuration for our application. It defines a Settings class using Pydantic's BaseSettings, which allows us to easily manage and access our application's configuration settings throughout the codebase. This includes settings for Firebase, the GLM AI model, Google API keys, authentication parameters, and CORS allowed origins. By centralizing our configuration in this file, we can keep our code organized and make it easier to manage different environments (development, staging, production) by simply changing the environment variables without needing to modify the code. This approach promotes clean code and makes it easier to maintain and update our application's configuration as needed.

from pydantic import field_validator
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
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        """Accept common deployment labels from host-level DEBUG variables."""
        if isinstance(value, str) and value.lower() == "release":
            return False
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
