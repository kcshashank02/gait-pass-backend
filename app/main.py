from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.core.database import connect_to_mongodb, close_mongodb_connection
from app.routers import auth, admin, face_recognition, wallet, stations, automated_journeys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Gait-Pass Backend API...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"ML Service URL: {settings.ML_SERVICE_URL}")
    await connect_to_mongodb()
    logger.info("MongoDB connected")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await close_mongodb_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# ✅ Parse CORS origins from settings
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
logger.info(f"CORS Origins: {origins}")

# ✅ Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(admin.router, prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])
app.include_router(face_recognition.router, prefix=f"{settings.API_V1_STR}/face", tags=["Face Recognition"])
app.include_router(wallet.router, prefix=f"{settings.API_V1_STR}/wallet", tags=["Wallet"])
app.include_router(stations.router, prefix=f"{settings.API_V1_STR}/stations", tags=["Stations"])
app.include_router(automated_journeys.router, prefix=f"{settings.API_V1_STR}/automated-journey", tags=["Journey"])

@app.get("/")
async def root():
    return {
        "message": "Gait-Pass Backend API",
        "status": "running",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "features": [
            "User authentication & authorization",
            "Face recognition via ML microservice",
            "Wallet management",
            "Station management",
            "Automated journey tracking",
            "Admin dashboard"
        ]
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": "connected",
        "ml_service_url": settings.ML_SERVICE_URL,
        "environment": settings.ENVIRONMENT
    }
