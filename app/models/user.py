from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.users

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt (max 72 bytes)
        
        The issue: bcrypt has a 72-byte limit, not 72-character limit.
        Some special characters take multiple bytes in UTF-8.
        """
        # Truncate to 72 characters first (safer than byte truncation)
        if len(password) > 72:
            password = password[:72]
        
        # Now hash (passlib handles the rest)
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password"""
        # Truncate to 72 characters for verification too
        if len(plain_password) > 72:
            plain_password = plain_password[:72]
        
        return pwd_context.verify(plain_password, hashed_password)

    async def create_user(self, user_data: dict) -> dict:
        """Create new user"""
        try:
            # Check if user already exists
            existing_user = await self.collection.find_one({"email": user_data["email"]})

            if existing_user:
                raise ValueError("User with this email already exists")

            # Just set defaults
            user_data["created_at"] = datetime.utcnow()
            user_data["updated_at"] = datetime.utcnow()
            user_data["is_active"] = True
            user_data["role"] = user_data.get("role", "user")
            user_data["wallet_balance"] = 0.0
            user_data["last_login"] = None

            # Insert user
            result = await self.collection.insert_one(user_data)
            user_data["_id"] = result.inserted_id

            # Remove password from response
            user_data.pop("password", None)
            return user_data

        except Exception as e:
            logger.error(f"User creation failed: {e}")
            raise



    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with email and password"""
        try:
            user = await self.collection.find_one({"email": email, "is_active": True})
            if not user or not self.verify_password(password, user["password"]):
                return None
            
            # Update last login
            now = datetime.utcnow()
            await self.collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": now}}
            )
            
            # Remove password from response
            user.pop("password")
            user["last_login"] = now
            return user
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None

    async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        try:
            user = await self.collection.find_one(
                {"_id": ObjectId(user_id), "is_active": True}
            )
            if user:
                user.pop("password", None)
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            logger.error(f"Get user failed: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        try:
            user = await self.collection.find_one(
                {"email": email, "is_active": True}
            )
            if user:
                user.pop("password", None)
                user["_id"] = str(user["_id"])
            return user
        except Exception as e:
            logger.error(f"Get user by email failed: {e}")
            return None

    async def update_user(self, user_id: str, update_data: dict) -> Optional[Dict]:
        """Update user data"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            # Hash password if provided
            if "password" in update_data:
                update_data["password"] = self.hash_password(update_data["password"])
            
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            if result.modified_count:
                return await self.get_user_by_id(user_id)
            return None
            
        except Exception as e:
            logger.error(f"User update failed: {e}")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Soft delete user"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"User deletion failed: {e}")
            return False

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """Get all users (admin only)"""
        try:
            cursor = self.collection.find(
                {"is_active": True},
                {"password": 0}  # Exclude password
            ).skip(skip).limit(limit)
            
            users = []
            async for user in cursor:
                user["_id"] = str(user["_id"])
                users.append(user)
            return users
        except Exception as e:
            logger.error(f"Get all users failed: {e}")
            return []

    async def create_admin_user(self, admin_data: dict) -> dict:
        """Create admin user"""
        admin_data["role"] = "admin"
        return await self.create_user(admin_data)


