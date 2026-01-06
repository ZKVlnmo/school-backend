# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your-super-secret-jwt-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    DATABASE_URL: str = "sqlite:///./school.db"
    GEN_API_TOKEN: str  # ← ЗАГЛАВНЫМИ, как в .env

    class Config:
        env_file = ".env"

settings = Settings()