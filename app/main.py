from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import connect_to_mongodb, close_mongodb_connection
from app.routers import (
    auth,
    admin,
    face_recognition,
    wallet,
    stations,
    automated_journeys
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting FastAPI Backend...")
    await connect_to_mongodb()
    logger.info("📊 MongoDB connected")
    
    yield
    
    # Shutdown
    await close_mongodb_connection()
    logger.info("✅ Shutdown complete")

app = FastAPI(
    title="Gait-Pass Backend API",
    description="Facial Recognition Ticketing System",
    version="2.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(face_recognition.router, prefix="/api/face", tags=["Face Recognition"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
app.include_router(stations.router, prefix="/api/stations", tags=["Stations"])
app.include_router(automated_journeys.router, prefix="/api/automated-journey", tags=["Journey"])

@app.get("/")
async def root():
    return {
        "message": "Gait-Pass Backend API",
        "status": "running",
        "version": "2.0.0",
        "features": [
            "User authentication & authorization",
            "Face recognition (via ML microservice)",
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
        "ml_service_url": settings.ML_SERVICE_URL
    }





















# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from contextlib import asynccontextmanager
# import logging

# from app.core.config import settings
# from app.core.database import connect_to_mongodb, close_mongodb_connection
# from app.routers import (
#     auth,
#     admin,
#     face_recognition,
#     wallet,
#     stations,
#     automated_journeys
# )

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup
#     logger.info("🚀 Starting FastAPI Backend...")
#     await connect_to_mongodb()
#     logger.info("📊 MongoDB connected")
    
#     yield
    
#     # Shutdown
#     await close_mongodb_connection()
#     logger.info("✅ Shutdown complete")

# # Initialize FastAPI app
# app = FastAPI(
#     title="Gait-Pass Backend API",
#     version="2.0.0",
#     lifespan=lifespan
# )

# # Enable CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ✅ Include all routers
# app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
# app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
# app.include_router(face_recognition.router, prefix="/api/face", tags=["Face Recognition"])
# app.include_router(wallet.router, prefix="/api/wallet", tags=["Wallet"])
# app.include_router(stations.router, prefix="/api/stations", tags=["Stations"])
# app.include_router(automated_journeys.router, prefix="/api/automated-journey", tags=["Journey"])

# # Root route
# @app.get("/")
# async def root():
#     return {
#         "message": "Gait-Pass Backend API",
#         "status": "running",
#         "version": "2.0.0"
#     }

# # Health check route
# @app.get("/health")
# async def health():
#     return {
#         "status": "healthy",
#         "database": "connected"
#     }

# # Uvicorn entry point
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(
#         "app.main:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info"
#     )
