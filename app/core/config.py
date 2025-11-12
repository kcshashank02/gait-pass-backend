from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Gait-Pass Facial Recognition Ticketing System"
    VERSION: str = "2.0.0"
    
    # Security / JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # Database
    MONGODB_URL: str
    DATABASE_NAME: str = Field(default="gaitpass")
    
    # ML Service URL
    ML_SERVICE_URL: str = Field(default="http://localhost:7860")
    
    # ✅ CORS Origins (comma-separated)
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173"
    )
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Initialize settings
settings = Settings()
