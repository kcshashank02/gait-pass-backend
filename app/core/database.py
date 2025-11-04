from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

# Global MongoDB instance
mongodb = MongoDB()

async def connect_to_mongodb():
    """Create database connection"""
    try:
        # mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        # database_name = os.getenv("DATABASE_NAME", "gaitpass")  # ✅ Consistent name
        mongodb_url = os.getenv("MONGODB_URL", "mongodb+srv://gait_pass:mSK3VBldgKTm6pEC@cluster0.sqsnt9a.mongodb.net/")
        database_name = os.getenv("DATABASE_NAME", "gaitpass")  # ✅ Consistent name
        logger.info(f"Connecting to MongoDB...")
        
        # Create client
        mongodb.client = AsyncIOMotorClient(mongodb_url)
        mongodb.db = mongodb.client[database_name]
        
        # Test connection
        await mongodb.client.admin.command('ping')
        logger.info(f"✅ MongoDB connected successfully (Database: {database_name})")
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise

async def close_mongodb_connection():
    """Close database connection"""
    try:
        if mongodb.client is not None:
            mongodb.client.close()
            logger.info("MongoDB connection closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")

async def get_database() -> AsyncIOMotorDatabase:
    """Get database instance for dependency injection"""
    if mongodb.db is None:
        raise RuntimeError("Database not initialized")
    return mongodb.db



















# from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
# from typing import Optional
# import os
# import logging

# logger = logging.getLogger(__name__)

# class MongoDB:
#     client: Optional[AsyncIOMotorClient] = None
#     db: Optional[AsyncIOMotorDatabase] = None

# # Global MongoDB instance
# mongodb = MongoDB()

# async def connect_to_mongodb():
#     """Create database connection"""
#     try:
#         mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
#         database_name = os.getenv("DATABASE_NAME", "gait_1")
        
#         logger.info(f"Connecting to MongoDB at {mongodb_url}")
        
#         # Create client
#         mongodb.client = AsyncIOMotorClient(mongodb_url)
#         mongodb.db = mongodb.client[database_name]
        
#         # Test connection
#         await mongodb.client.admin.command('ping')
#         logger.info("✅ MongoDB connected successfully")
        
#     except Exception as e:
#         logger.error(f"❌ MongoDB connection failed: {e}")
#         raise

# async def close_mongodb_connection():
#     """Close database connection"""
#     try:
#         if mongodb.client is not None:  # ✅ Fixed: explicit None check
#             mongodb.client.close()
#             logger.info("✅ MongoDB connection closed")
#     except Exception as e:
#         logger.error(f"❌ Error closing MongoDB connection: {e}")

# async def get_database() -> AsyncIOMotorDatabase:
#     """Get database instance for dependency injection"""
#     if mongodb.db is None:  # ✅ Fixed: explicit None check
#         raise RuntimeError("Database not initialized")
#     return mongodb.db


