from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, EmailStr

from app.core.database import get_database
from app.models.user import User
from app.core.security import get_current_admin_user

logger = logging.getLogger(__name__)
router = APIRouter( tags=["admin"])


# -------------------
# Pydantic Model for Admin Creation
# -------------------
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    phone: str
    date_of_birth: Optional[str] = None
    role: Optional[str] = "admin"  # Ignored, forced to admin


# -------------------
# Admin Dashboard
# -------------------
@router.get("/dashboard")
async def admin_dashboard(
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    try:
        total_users = await db.users.count_documents({"role": "user", "is_active": True})
        total_admins = await db.users.count_documents({"role": "admin", "is_active": True})
        total_face_registrations = await db.face_data.count_documents({"is_active": True})

        return {
            "message": f"Welcome, Admin {admin_user['first_name']}",
            "statistics": {
                "total_users": total_users,
                "total_admins": total_admins,
                "total_face_registrations": total_face_registrations,
                "active_stations": 0
            }
        }
    except Exception as e:
        logger.error(f"Admin dashboard failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load dashboard"
        )

# Existing endpoint - UPDATE to only show regular users
@router.get("/users")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Get list of regular users (not admins)"""
    try:
        user_model = User(db)
        
        # ✅ Filter only regular users (role="user")
        users_cursor = user_model.collection.find(
            {"role": "user"}  # ✅ Only regular users
        ).skip(skip).limit(limit)
        
        users = await users_cursor.to_list(length=limit)
        total = await user_model.collection.count_documents({"role": "user"})
        
        # Format user data
        users_list = []
        for user in users:
            users_list.append({
                "id": str(user["_id"]),
                "email": user["email"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "phone": user.get("phone"),
                "role": user["role"],
                "is_active": user.get("is_active", True),
                "created_at": user.get("created_at")
            })
        
        return {
            "success": True,
            "users": users_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"List users failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


# ✅ NEW endpoint - List only admin users
@router.get("/admins")
async def list_admins(
    skip: int = 0,
    limit: int = 20,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Get list of admin users"""
    try:
        user_model = User(db)
        
        # ✅ Filter only admin users (role="admin")
        admins_cursor = user_model.collection.find(
            {"role": "admin"}  # ✅ Only admins
        ).skip(skip).limit(limit)
        
        admins = await admins_cursor.to_list(length=limit)
        total = await user_model.collection.count_documents({"role": "admin"})
        
        # Format admin data
        admins_list = []
        for admin in admins:
            admins_list.append({
                "id": str(admin["_id"]),
                "email": admin["email"],
                "first_name": admin["first_name"],
                "last_name": admin["last_name"],
                "phone": admin.get("phone"),
                "role": admin["role"],
                "is_active": admin.get("is_active", True),
                "created_at": admin.get("created_at"),
                "last_login": admin.get("last_login")
            })
        
        return {
            "success": True,
            "admins": admins_list,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"List admins failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admins"
        )



# -------------------
# Get User by ID
# -------------------
@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    try:
        user_model = User(db)
        user = await user_model.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        user["_id"] = str(user["_id"])
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by ID failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


# -------------------
# Delete User
# -------------------
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    try:
        user_model = User(db)
        deleted = await user_model.delete_user(user_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {"success": True, "message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deletion failed"
        )
    


# ✅ Delete regular user (also deletes their wallet, face data, journeys)
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Delete a regular user and all associated data"""
    try:
        user_model = User(db)
        
        # Get user to verify it exists and is not an admin
        user = await user_model.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting admin users through this endpoint
        if user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete admin users through this endpoint. Use /admins/{admin_id} instead"
            )
        
        # Delete associated data
        # 1. Delete wallet
        await db.wallets.delete_one({"user_id": ObjectId(user_id)})
        
        # 2. Delete face data
        await db.face_data.delete_many({"user_id": ObjectId(user_id)})
        
        # 3. Delete journeys
        await db.journeys.delete_many({"user_id": ObjectId(user_id)})
        
        # 4. Delete user
        await db.users.delete_one({"_id": ObjectId(user_id)})
        
        logger.info(f"User {user_id} ({user['email']}) deleted by admin {admin_user['email']}")
        
        return {
            "success": True,
            "message": "User and all associated data deleted successfully",
            "deleted_user_id": user_id,
            "deleted_user_email": user["email"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# ✅ Delete admin user
@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Delete an admin user. Cannot delete yourself."""
    try:
        user_model = User(db)
        
        # Get admin to verify it exists
        target_admin = await user_model.get_user_by_id(admin_id)
        if not target_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin user not found"
            )
        
        # Verify target is actually an admin
        if target_admin.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user is not an admin. Use /users/{user_id} endpoint instead"
            )
        
        # Prevent self-deletion
        if str(target_admin["_id"]) == str(admin_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete your own admin account"
            )
        
        # Check if this is the last admin
        admin_count = await db.users.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete the last admin user. Create another admin first"
            )
        
        # Delete admin (no wallet or face data to delete)
        await db.users.delete_one({"_id": ObjectId(admin_id)})
        
        logger.info(f"Admin {admin_id} ({target_admin['email']}) deleted by admin {admin_user['email']}")
        
        return {
            "success": True,
            "message": "Admin user deleted successfully",
            "deleted_admin_id": admin_id,
            "deleted_admin_email": target_admin["email"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete admin failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete admin"
        )




@router.post("/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin(
    user_data: AdminUserCreate,
    admin_user: dict = Depends(get_current_admin_user),  # ✅ Only admins can create admins
    db = Depends(get_database)
):
    """Create a new admin user. Only accessible by existing admins."""
    try:
        user_model = User(db)
        
        # Check if email already exists
        existing_user = await user_model.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Prepare admin data
        admin_data = {
            "email": user_data.email,
            "password": user_model.hash_password(user_data.password),
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "date_of_birth": user_data.date_of_birth,
            "role": "admin",  # ✅ Force admin role
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # ✅ Create admin user (NO WALLET!)
        result = await db.users.insert_one(admin_data)
        admin_data["_id"] = result.inserted_id
        
        # ✅ DO NOT create wallet for admin users
        
        logger.info(f"Admin user created: {user_data.email} by {admin_user['email']}")
        
        return {
            "success": True,
            "message": "Admin user created successfully",
            "user": {
                "id": str(admin_data["_id"]),
                "email": admin_data["email"],
                "first_name": admin_data["first_name"],
                "last_name": admin_data["last_name"],
                "phone": admin_data["phone"],
                "role": admin_data["role"],
                "is_active": admin_data["is_active"],
                "created_at": admin_data["created_at"].isoformat()
                # ✅ NO wallet_balance field for admins
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}"
        )





