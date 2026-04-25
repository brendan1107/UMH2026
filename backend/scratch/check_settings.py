import sys
import os
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(r"c:\Users\Louis Lau\Desktop\UMH2026\backend")
sys.path.append(str(backend_dir))

try:
    from app.config import settings
    print(f"APP_ENV: {settings.APP_ENV}")
    print(f"GLM_API_KEY exists: {bool(settings.GLM_API_KEY)}")
    print(f"GLM_API_BASE_URL exists: {bool(settings.GLM_API_BASE_URL)}")
    print(f"GLM_API_BASE_URL: {settings.GLM_API_BASE_URL}")
    print(f"GLM_MODEL_NAME: {settings.GLM_MODEL_NAME}")
    print(f"GLM_MAX_TOKENS: {settings.GLM_MAX_TOKENS}")
except Exception as e:
    print(f"Error loading settings: {e}")
