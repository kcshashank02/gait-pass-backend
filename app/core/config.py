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
    DATABASE_NAME: str = Field(default="gaitpass")  # ✅ Added database name
    
    # ML Service URL
    ML_SERVICE_URL: str = Field(default="http://localhost:7860")
    
    # Environment
    ENVIRONMENT: str = "development"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Initialize settings
settings = Settings()

















# from pydantic_settings import BaseSettings
# from pydantic import Field

# class Settings(BaseSettings):
#     # MongoDB
#     MONGODB_URL: str

#     # JWT Configuration
#     JWT_SECRET: str
#     JWT_ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
#     REFRESH_TOKEN_EXPIRE_DAYS: int = 30

#     # ML Service URL ✅ NEW
#     ML_SERVICE_URL: str = Field(default="http://localhost:7860")

#     # Environment
#     ENVIRONMENT: str = "development"

#     class Config:
#         env_file = ".env"
#         case_sensitive = True

# # Initialize settings
# settings = Settings()
















# # from pydantic_settings import BaseSettings
# # from typing import Optional
# # import os

# # class Settings(BaseSettings):
# #     # API Configuration
# #     API_V1_STR: str = "/api"
# #     PROJECT_NAME: str = "Facial Recognition Ticketing System"
# #     VERSION: str = "2.0.0"
    
# #     # Security
# #     SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this")
# #     ALGORITHM: str = "HS256"
# #     ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
# #     REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
# #     # Database
# #     MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
# #     DATABASE_NAME: str = os.getenv("DATABASE_NAME", "facial_ticketing_system")
    
# #     # ML Configuration
# #     ML_MODEL_PATH: str = os.getenv("ML_MODEL_PATH", "models/")
# #     FACE_RECOGNITION_THRESHOLD: float = 0.4
# #     DETECTION_SIZE: tuple = (640, 640)
    
# #     # File Upload
# #     UPLOAD_DIR: str = "uploads"
# #     MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
# #     ALLOWED_IMAGE_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    
# #     # Video Processing
# #     VIDEO_FRAME_RATE: int = 30
# #     MAX_VIDEO_FRAME_SIZE: int = 2 * 1024 * 1024  # 2MB
    
# #     # CORS
# #     BACKEND_CORS_ORIGINS: list = ["*"]
    
# #     # Logging
# #     LOG_LEVEL: str = "INFO"
    
# #     class Config:
# #         env_file = ".env"
# #         case_sensitive = True

# # settings = Settings()
