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

            # ❌ REMOVE THIS LINE - Password is already hashed in auth.py
            # user_data["password"] = self.hash_password(user_data["password"])

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













































# from passlib.context import CryptContext
# from motor.motor_asyncio import AsyncIOMotorDatabase
# from datetime import datetime
# from bson import ObjectId

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# class User:
#     def __init__(self, db: AsyncIOMotorDatabase):
#         self.collection = db.users

#     # -----------------------------
#     # Password helpers
#     # -----------------------------
#     @staticmethod
#     def hash_password(password: str) -> str:
#         """Hash password with bcrypt (max 72 bytes)"""
#         # Truncate BEFORE encoding to ensure byte length
#         password_bytes = password.encode('utf-8')[:72]
#         password_truncated = password_bytes.decode('utf-8', errors='ignore')
#         return pwd_context.hash(password_truncated)

#     @staticmethod
#     def verify_password(plain_password: str, hashed_password: str) -> bool:
#         """Verify password"""
#         password_bytes = plain_password.encode('utf-8')[:72]
#         password_truncated = password_bytes.decode('utf-8', errors='ignore')
#         return pwd_context.verify(password_truncated, hashed_password)

#     # -----------------------------
#     # User creation
#     # -----------------------------
#     async def create_user(self, user_data: dict):
#         """Create new user"""
#         result = await self.collection.insert_one(user_data)
#         created_user = await self.collection.find_one({"_id": result.inserted_id})
#         return created_user

#     async def get_user_by_email(self, email: str):
#         """Get user by email"""
#         return await self.collection.find_one({"email": email})

#     async def get_user_by_id(self, user_id: str):
#         """Get user by ID"""
#         try:
#             return await self.collection.find_one({"_id": ObjectId(user_id)})
#         except Exception:
#             return None

#     # -----------------------------
#     # Authentication
#     # -----------------------------
#     async def authenticate_user(self, email: str, password: str):
#         """Authenticate user"""
#         user = await self.get_user_by_email(email)
#         if not user:
#             return None
#         if not self.verify_password(password, user["password"]):
#             return None
        
#         # Update last login
#         now = datetime.utcnow()
#         await self.collection.update_one(
#             {"_id": user["_id"]},
#             {"$set": {"last_login": now}}
#         )
        
#         user["last_login"] = now
#         return user

#     # -----------------------------
#     # User updates
#     # -----------------------------
#     async def update_user(self, user_id: str, update_data: dict):
#         """Update user"""
#         # If updating password, hash it
#         if "password" in update_data:
#             update_data["password"] = self.hash_password(update_data["password"])
        
#         update_data["updated_at"] = datetime.utcnow()
        
#         await self.collection.update_one(
#             {"_id": ObjectId(user_id)},
#             {"$set": update_data}
#         )
#         return await self.get_user_by_id(user_id)








































# # from motor.motor_asyncio import AsyncIOMotorDatabase
# # from bson import ObjectId
# # from typing import Optional, Dict, List
# # from datetime import datetime
# # from passlib.context import CryptContext
# # import logging

# # logger = logging.getLogger(__name__)
# # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# # class User:
# #     def __init__(self, db: AsyncIOMotorDatabase):
# #         self.collection = db.users

# #     # -----------------------------
# #     # Password helpers with bcrypt-safe truncation
# #     # -----------------------------
# #     @staticmethod
# #     def hash_password(password: str) -> str:
# #         """Hash password with bcrypt (max 72 bytes)"""
# #         if len(password.encode('utf-8')) > 72:
# #             password = password[:72]
# #         return pwd_context.hash(password)

# #     @staticmethod
# #     def verify_password(plain_password: str, hashed_password: str) -> bool:
# #         """Verify password"""
# #         if len(plain_password.encode('utf-8')) > 72:
# #             plain_password = plain_password[:72]
# #         return pwd_context.verify(plain_password, hashed_password)

# #     # -----------------------------
# #     # User creation
# #     # -----------------------------
# #     async def create_user(self, user_data: dict):
# #         """Create new user"""
# #         result = await self.collection.insert_one(user_data)
# #         created_user = await self.collection.find_one({"_id": result.inserted_id})
# #         return created_user

# #     async def create_admin_user(self, admin_data: Dict) -> Dict:
# #         """Create admin user"""
# #         admin_data["role"] = "admin"
# #         if "wallet_balance" not in admin_data:
# #             admin_data["wallet_balance"] = 0.0
# #         if "date_of_birth" not in admin_data:
# #             admin_data["date_of_birth"] = None
# #         return await self.create_user(admin_data)

# #     # -----------------------------
# #     # Authentication
# #     # -----------------------------
# #     async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
# #         try:
# #             user = await self.collection.find_one({"email": email, "is_active": True})
# #             if user is None or not self.verify_password(password, user["password"]):
# #                 return None

# #             await self.collection.update_one(
# #                 {"_id": user["_id"]},
# #                 {"$set": {"last_login": datetime.utcnow()}}
# #             )
# #             user.pop("password")
# #             user["_id"] = str(user["_id"])
# #             return user
# #         except Exception as e:
# #             logger.error(f"Authentication failed: {e}")
# #             return None

# #     # -----------------------------
# #     # CRUD operations
# #     # -----------------------------
# #     async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
# #         try:
# #             user = await self.collection.find_one({"_id": ObjectId(user_id), "is_active": True})
# #             if user:
# #                 user.pop("password", None)
# #                 user["_id"] = str(user["_id"])
# #             return user
# #         except Exception as e:
# #             logger.error(f"Get user by ID failed: {e}")
# #             return None

# #     async def get_user_by_email(self, email: str):
# #         """Get user by email"""
# #         return await self.collection.find_one({"email": email})

# #     async def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
# #         try:
# #             update_data["updated_at"] = datetime.utcnow()
# #             if "password" in update_data:
# #                 update_data["password"] = self.hash_password(update_data["password"])

# #             result = await self.collection.update_one(
# #                 {"_id": ObjectId(user_id)},
# #                 {"$set": update_data}
# #             )
# #             if result.modified_count:
# #                 return await self.get_user_by_id(user_id)
# #             return None
# #         except Exception as e:
# #             logger.error(f"User update failed: {e}")
# #             raise

# #     async def delete_user(self, user_id: str) -> bool:
# #         try:
# #             result = await self.collection.update_one(
# #                 {"_id": ObjectId(user_id)},
# #                 {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
# #             )
# #             return result.modified_count > 0
# #         except Exception as e:
# #             logger.error(f"User deletion failed: {e}")
# #             return False

# #     async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict]:
# #         try:
# #             cursor = self.collection.find({"is_active": True}, {"password": 0}).skip(skip).limit(limit)
# #             users = []
# #             async for user in cursor:
# #                 user["_id"] = str(user["_id"])
# #                 users.append(user)
# #             return users
# #         except Exception as e:
# #             logger.error(f"Get all users failed: {e}")
# #             return []











# # # from motor.motor_asyncio import AsyncIOMotorDatabase
# # # from bson import ObjectId
# # # from typing import Optional, Dict, List
# # # from datetime import datetime
# # # from passlib.context import CryptContext
# # # import logging

# # # logger = logging.getLogger(__name__)
# # # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# # # class User:
# # #     def __init__(self, db: AsyncIOMotorDatabase):
# # #         self.collection = db.users

# # #     # -----------------------------
# # #     # Password helpers with bcrypt-safe truncation
# # #     # -----------------------------
# # #     @staticmethod
# # #     def hash_password(password: str) -> str:
# # #         """Hash password with bcrypt (max 72 bytes)"""
# # #         # ✅ Safety truncation (should never reach here due to Pydantic validation)
# # #         if len(password.encode('utf-8')) > 72:
# # #             password = password[:72]
# # #         return pwd_context.hash(password)

# # #     @staticmethod
# # #     def verify_password(plain_password: str, hashed_password: str) -> bool:
# # #         """Verify password"""
# # #         # ✅ Safety truncation for verification
# # #         if len(plain_password.encode('utf-8')) > 72:
# # #             plain_password = plain_password[:72]
# # #         return pwd_context.verify(plain_password, hashed_password)

# # #     # -----------------------------
# # #     # User creation
# # #     # -----------------------------
# # #     async def create_user(self, user_data: Dict) -> Dict:
# # #         """Create new user"""
# # #         try:
# # #             existing_user = await self.collection.find_one({
# # #                 "$or": [
# # #                     {"email": user_data["email"]},
# # #                     {"phone": user_data.get("phone")}
# # #                 ]
# # #             })

# # #             if existing_user:
# # #                 if existing_user["email"] == user_data["email"]:
# # #                     raise ValueError("User with this email already exists")
# # #                 if existing_user.get("phone") == user_data.get("phone"):
# # #                     raise ValueError("User with this phone number already exists")

# # #             user_data["password"] = self.hash_password(user_data["password"])
# # #             user_data["created_at"] = datetime.utcnow()
# # #             user_data["updated_at"] = datetime.utcnow()
# # #             user_data["is_active"] = True
# # #             user_data["role"] = user_data.get("role", "user")
# # #             user_data["wallet_balance"] = 0.0
# # #             user_data["last_login"] = None
            
# # #             if "date_of_birth" not in user_data:
# # #                 user_data["date_of_birth"] = None

# # #             result = await self.collection.insert_one(user_data)
# # #             user_data["_id"] = result.inserted_id
# # #             user_data.pop("password")
# # #             return user_data

# # #         except ValueError as e:
# # #             logger.error(f"Validation error: {e}")
# # #             raise
# # #         except Exception as e:
# # #             logger.error(f"User creation failed: {e}")
# # #             raise

# # #     async def create_admin_user(self, admin_data: Dict) -> Dict:
# # #         """Create admin user"""
# # #         admin_data["role"] = "admin"
# # #         if "wallet_balance" not in admin_data:
# # #             admin_data["wallet_balance"] = 0.0
# # #         if "date_of_birth" not in admin_data:
# # #             admin_data["date_of_birth"] = None
# # #         return await self.create_user(admin_data)

# # #     # -----------------------------
# # #     # Authentication
# # #     # -----------------------------
# # #     async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
# # #         try:
# # #             user = await self.collection.find_one({"email": email, "is_active": True})
# # #             if user is None or not self.verify_password(password, user["password"]):
# # #                 return None

# # #             await self.collection.update_one(
# # #                 {"_id": user["_id"]},
# # #                 {"$set": {"last_login": datetime.utcnow()}}
# # #             )
# # #             user.pop("password")
# # #             user["_id"] = str(user["_id"])
# # #             return user
# # #         except Exception as e:
# # #             logger.error(f"Authentication failed: {e}")
# # #             return None

# # #     # -----------------------------
# # #     # CRUD operations
# # #     # -----------------------------
# # #     async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
# # #         try:
# # #             user = await self.collection.find_one({"_id": ObjectId(user_id), "is_active": True})
# # #             if user:
# # #                 user.pop("password", None)
# # #                 user["_id"] = str(user["_id"])
# # #             return user
# # #         except Exception as e:
# # #             logger.error(f"Get user by ID failed: {e}")
# # #             return None

# # #     async def get_user_by_email(self, email: str) -> Optional[Dict]:
# # #         try:
# # #             user = await self.collection.find_one({"email": email, "is_active": True})
# # #             if user:
# # #                 user.pop("password", None)
# # #                 user["_id"] = str(user["_id"])
# # #             return user
# # #         except Exception as e:
# # #             logger.error(f"Get user by email failed: {e}")
# # #             return None

# # #     async def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
# # #         try:
# # #             update_data["updated_at"] = datetime.utcnow()
# # #             if "password" in update_data:
# # #                 update_data["password"] = self.hash_password(update_data["password"])

# # #             result = await self.collection.update_one(
# # #                 {"_id": ObjectId(user_id)},
# # #                 {"$set": update_data}
# # #             )
# # #             if result.modified_count:
# # #                 return await self.get_user_by_id(user_id)
# # #             return None
# # #         except Exception as e:
# # #             logger.error(f"User update failed: {e}")
# # #             raise

# # #     async def delete_user(self, user_id: str) -> bool:
# # #         try:
# # #             result = await self.collection.update_one(
# # #                 {"_id": ObjectId(user_id)},
# # #                 {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
# # #             )
# # #             return result.modified_count > 0
# # #         except Exception as e:
# # #             logger.error(f"User deletion failed: {e}")
# # #             return False

# # #     async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict]:
# # #         try:
# # #             cursor = self.collection.find({"is_active": True}, {"password": 0}).skip(skip).limit(limit)
# # #             users = []
# # #             async for user in cursor:
# # #                 user["_id"] = str(user["_id"])
# # #                 users.append(user)
# # #             return users
# # #         except Exception as e:
# # #             logger.error(f"Get all users failed: {e}")
# # #             return []


















# # # # from motor.motor_asyncio import AsyncIOMotorDatabase
# # # # from bson import ObjectId
# # # # from typing import Optional, Dict, List
# # # # from datetime import datetime
# # # # from passlib.context import CryptContext
# # # # import logging

# # # # logger = logging.getLogger(__name__)
# # # # pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# # # # class User:
# # # #     def __init__(self, db: AsyncIOMotorDatabase):
# # # #         self.collection = db.users  # MongoDB collection

# # # #     # -----------------------------
# # # #     # Password helpers
# # # #     # -----------------------------
# # # #     @staticmethod
# # # #     def hash_password(password: str) -> str:
# # # #         """Hash password"""
# # # #         return pwd_context.hash(password)

# # # #     @staticmethod
# # # #     def verify_password(plain_password: str, hashed_password: str) -> bool:
# # # #         """Verify password"""
# # # #         return pwd_context.verify(plain_password, hashed_password)

# # # #     # -----------------------------
# # # #     # User creation
# # # #     # -----------------------------
# # # #     # async def create_user(self, user_data: Dict) -> Dict:
# # # #     # """Create new user"""
# # # #     # try:
# # # #     #     # Check for existing user FIRST - before any modifications
# # # #     #     existing_user = await self.collection.find_one({
# # # #     #         "$or": [
# # # #     #             {"email": user_data["email"]},
# # # #     #             {"phone": user_data.get("phone")}
# # # #     #         ]
# # # #     #     })

# # # #     #     # If user exists, raise error IMMEDIATELY
# # # #     #     if existing_user is not None:
# # # #     #         if existing_user["email"] == user_data["email"]:
# # # #     #             raise ValueError("User with this email already exists")
# # # #     #         if existing_user.get("phone") == user_data.get("phone"):
# # # #     #             raise ValueError("User with this phone number already exists")

# # # #     #     # Only proceed if no existing user found
# # # #     #     user_data["password"] = self.hash_password(user_data["password"])
# # # #     #     user_data["created_at"] = datetime.utcnow()
# # # #     #     user_data["updated_at"] = datetime.utcnow()
# # # #     #     user_data["is_active"] = True
# # # #     #     user_data["role"] = user_data.get("role", "user")
# # # #     #     user_data["wallet_balance"] = 0.0
# # # #     #     user_data["last_login"] = None
        
# # # #     #     if "date_of_birth" not in user_data:
# # # #     #         user_data["date_of_birth"] = None

# # # #     #     # Insert into database
# # # #     #     result = await self.collection.insert_one(user_data)
# # # #     #     user_data["_id"] = result.inserted_id
# # # #     #     user_data.pop("password")  # Remove password from response
# # # #     #     return user_data

# # # #     # except ValueError as e:
# # # #     #     # Re-raise ValueError (duplicate email/phone)
# # # #     #     logger.error(f"Validation error: {e}")
# # # #     #     raise
# # # #     # except Exception as e:
# # # #     #     logger.error(f"User creation failed: {e}")
# # # #     #     raise

# # # #     async def create_user(self, user_data: Dict) -> Dict:
# # # #         """Create new user"""
# # # #         try:
# # # #             # Check for existing user FIRST - before any modifications
# # # #             existing_user = await self.collection.find_one({
# # # #                 "$or": [
# # # #                     {"email": user_data["email"]},
# # # #                     {"phone": user_data.get("phone")}
# # # #                 ]
# # # #             })

# # # #             # If user exists, raise error IMMEDIATELY
# # # #             if existing_user is not None:
# # # #                 if existing_user["email"] == user_data["email"]:
# # # #                     raise ValueError("User with this email already exists")
# # # #                 if existing_user.get("phone") == user_data.get("phone"):
# # # #                     raise ValueError("User with this phone number already exists")

# # # #             # Only proceed if no existing user found
# # # #             user_data["password"] = self.hash_password(user_data["password"])
# # # #             user_data["created_at"] = datetime.utcnow()
# # # #             user_data["updated_at"] = datetime.utcnow()
# # # #             user_data["is_active"] = True
# # # #             user_data["role"] = user_data.get("role", "user")
# # # #             user_data["wallet_balance"] = 0.0
# # # #             user_data["last_login"] = None
            
# # # #             if "date_of_birth" not in user_data:
# # # #                 user_data["date_of_birth"] = None

# # # #             # Insert into database
# # # #             result = await self.collection.insert_one(user_data)
# # # #             user_data["_id"] = result.inserted_id
# # # #             user_data.pop("password")  # Remove password from response
# # # #             return user_data

# # # #         except ValueError as e:
# # # #             # Re-raise ValueError (duplicate email/phone)
# # # #             logger.error(f"Validation error: {e}")
# # # #             raise
# # # #         except Exception as e:
# # # #             logger.error(f"User creation failed: {e}")
# # # #             raise


# # # #     async def create_admin_user(self, admin_data: Dict) -> Dict:
# # # #         """Create admin user"""
# # # #         admin_data["role"] = "admin"
# # # #         if "wallet_balance" not in admin_data:
# # # #             admin_data["wallet_balance"] = 0.0
# # # #         if "date_of_birth" not in admin_data:
# # # #             admin_data["date_of_birth"] = None
# # # #         return await self.create_user(admin_data)

# # # #     # -----------------------------
# # # #     # Authentication
# # # #     # -----------------------------
# # # #     async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
# # # #         """Authenticate user with email and password"""
# # # #         try:
# # # #             user = await self.collection.find_one({"email": email, "is_active": True})
# # # #             if user is None or not self.verify_password(password, user["password"]):
# # # #                 return None

# # # #             # Update last login timestamp
# # # #             await self.collection.update_one(
# # # #                 {"_id": user["_id"]},
# # # #                 {"$set": {"last_login": datetime.utcnow()}}
# # # #             )
# # # #             user.pop("password")
# # # #             user["_id"] = str(user["_id"])
# # # #             return user

# # # #         except Exception as e:
# # # #             logger.error(f"Authentication failed: {e}")
# # # #             return None

# # # #     # -----------------------------
# # # #     # CRUD operations
# # # #     # -----------------------------
# # # #     async def get_user_by_id(self, user_id: str) -> Optional[Dict]:
# # # #         try:
# # # #             user = await self.collection.find_one({"_id": ObjectId(user_id), "is_active": True})
# # # #             if user:
# # # #                 user.pop("password", None)
# # # #                 user["_id"] = str(user["_id"])
# # # #             return user
# # # #         except Exception as e:
# # # #             logger.error(f"Get user by ID failed: {e}")
# # # #             return None

# # # #     async def get_user_by_email(self, email: str) -> Optional[Dict]:
# # # #         try:
# # # #             user = await self.collection.find_one({"email": email, "is_active": True})
# # # #             if user:
# # # #                 user.pop("password", None)
# # # #                 user["_id"] = str(user["_id"])
# # # #             return user
# # # #         except Exception as e:
# # # #             logger.error(f"Get user by email failed: {e}")
# # # #             return None

# # # #     async def update_user(self, user_id: str, update_data: Dict) -> Optional[Dict]:
# # # #         try:
# # # #             update_data["updated_at"] = datetime.utcnow()
# # # #             if "password" in update_data:
# # # #                 update_data["password"] = self.hash_password(update_data["password"])

# # # #             result = await self.collection.update_one(
# # # #                 {"_id": ObjectId(user_id)},
# # # #                 {"$set": update_data}
# # # #             )
# # # #             if result.modified_count:
# # # #                 return await self.get_user_by_id(user_id)
# # # #             return None
# # # #         except Exception as e:
# # # #             logger.error(f"User update failed: {e}")
# # # #             raise

# # # #     async def delete_user(self, user_id: str) -> bool:
# # # #         """Soft delete user"""
# # # #         try:
# # # #             result = await self.collection.update_one(
# # # #                 {"_id": ObjectId(user_id)},
# # # #                 {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
# # # #             )
# # # #             return result.modified_count > 0
# # # #         except Exception as e:
# # # #             logger.error(f"User deletion failed: {e}")
# # # #             return False

# # # #     # -----------------------------
# # # #     # List all users
# # # #     # -----------------------------
# # # #     async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[Dict]:
# # # #         try:
# # # #             cursor = self.collection.find({"is_active": True}, {"password": 0}).skip(skip).limit(limit)
# # # #             users = []
# # # #             async for user in cursor:
# # # #                 user["_id"] = str(user["_id"])
# # # #                 users.append(user)
# # # #             return users
# # # #         except Exception as e:
# # # #             logger.error(f"Get all users failed: {e}")
# # # #             return []






