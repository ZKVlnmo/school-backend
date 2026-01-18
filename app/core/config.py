from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your-super-secret-jwt-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    DATABASE_URL: str = "sqlite:///./school.db"
    GEN_API_TOKEN: str
    LNO_API_BASE_URL: str
    LNO_USERNAME: str
    LNO_PASSWORD: str
    LNO_ZDEKH_USERNAME: str
    LNO_ZDEKH_PASSWORD: str
    LNO_VASILIEVA_USERNAME: str
    LNO_VASILIEVA_PASSWORD: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()