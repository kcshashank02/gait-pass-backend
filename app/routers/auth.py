from fastapi import APIRouter, Depends, HTTPException, status
from app.core.database import get_database
from app.core.security import create_access_token, create_refresh_token, get_current_user, verify_token
from app.models.user import User
from app.models.wallet import Wallet
from app.schemas.auth import (
    UserRegistration,
    UserLogin,
    AdminLogin,
    TokenResponse,
    UserResponse,
    ChangePassword,
    RefreshTokenRequest,
    DeleteAccountRequest
)
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from app.models.user import User
from app.models.wallet import Wallet
from app.core.database import get_database
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegistration, db=Depends(get_database)):
    """User registration"""
    try:
        user_model = User(db)

        # ✅ Check if user already exists
        existing_user = await user_model.get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # ✅ Prepare user document
        user_dict = {
            "email": user_data.email,
            "password": user_model.hash_password(user_data.password),
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "date_of_birth": user_data.date_of_birth,
            "role": getattr(user_data, "role", "user"),  # default role = "user"
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        # ✅ Create user
        created_user = await user_model.create_user(user_dict)

        # ✅ Only create wallet for regular users
        if created_user.get("role") == "user":
            wallet_model = Wallet(db)
            await wallet_model.create_wallet_for_user(str(created_user["_id"]))

        # ✅ Return success response
        return {
            "success": True,
            "message": "User registered successfully! Please login to continue.",
            "user": {
                "id": str(created_user["_id"]),
                "email": created_user["email"],
                "first_name": created_user["first_name"],
                "last_name": created_user["last_name"],
                "phone": created_user["phone"],
                "role": created_user["role"],
                "created_at": created_user["created_at"].isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )




@router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin, db=Depends(get_database)):
    """User login"""
    try:
        user_model = User(db)
        user = await user_model.authenticate_user(login_data.email, login_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # ✅ FIX: Store user ID in token, not email
        access_token = create_access_token({
            "sub": str(user["_id"]),  # ✅ Use user ID
            "email": user["email"],
            "role": user["role"]
        })
        
        refresh_token = create_refresh_token({
            "sub": str(user["_id"]),  # ✅ Use user ID
            "email": user["email"]
        })
        
        # Get wallet balance
        wallet_model = Wallet(db)
        wallet = await wallet_model.get_wallet_by_user_id(str(user["_id"]))
        balance = wallet.get("balance", 0.0) if wallet else 0.0
        
        user_response = UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user["phone"],
            date_of_birth=user["date_of_birth"],
            role=user["role"],
            wallet_balance=balance,
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login")
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )



@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(login_data: AdminLogin, db=Depends(get_database)):
    """Admin login endpoint"""
    try:
        user_model = User(db)
        
        # Authenticate admin
        user = await user_model.authenticate_user(login_data.email, login_data.password)
        
        if not user or user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        
        # ✅ FIX: Create token with BOTH sub AND email (consistent with regular login)
        access_token = create_access_token(
            data={
                "sub": str(user["_id"]),      # User ID
                "email": user["email"],        # ✅ ADD THIS
                "role": user["role"]
            }
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": str(user["_id"]),
                "email": user["email"],        # ✅ ADD THIS
                "role": user["role"]
            }
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            user=UserResponse(
                id=str(user["_id"]),
                email=user["email"],
                first_name=user["first_name"],
                last_name=user["last_name"],
                phone=user["phone"],
                date_of_birth=user["date_of_birth"],
                role=user["role"],
                wallet_balance=None,  # Admins don't have wallets
                is_active=user["is_active"],
                created_at=user["created_at"],
                last_login=user.get("last_login")
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin login failed"
        )




@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get current user profile"""
    try:
        # Get wallet balance from wallets collection
        wallet_model = Wallet(db)
        wallet_balance = 0.0
        
        # Only get wallet for regular users (not admins)
        if current_user.get("role") == "user":
            balance = await wallet_model.get_balance(str(current_user["_id"]))
            wallet_balance = balance if balance is not None else 0.0
        
        return UserResponse(
            id=str(current_user["_id"]),
            email=current_user["email"],
            first_name=current_user["first_name"],
            last_name=current_user["last_name"],
            phone=current_user["phone"],
            date_of_birth=current_user["date_of_birth"],
            role=current_user["role"],
            wallet_balance=wallet_balance if current_user.get("role") == "user" else None,
            is_active=current_user["is_active"],
            created_at=current_user["created_at"],
            last_login=current_user.get("last_login")
        )
    except Exception as e:
        logger.error(f"Get profile failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.put("/change-password")
async def change_password(password_data: ChangePassword, current_user: dict = Depends(get_current_user), db = Depends(get_database)):
    """Change user password"""
    try:
        user_model = User(db)
        authenticated_user = await user_model.authenticate_user(current_user["email"], password_data.current_password)
        if not authenticated_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        await user_model.update_user(current_user["_id"], {"password": password_data.new_password})
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password change failed")


@router.post("/refresh")
async def refresh_access_token(
    token_data: RefreshTokenRequest,  # ✅ Accept from body, not query
    db=Depends(get_database)
):
    """Refresh access token"""
    try:
        payload = verify_token(token_data.refresh_token)
        
        if payload is None or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user ID from token
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Verify user still exists and is active
        user_model = User(db)
        user = await user_model.get_user_by_id(user_id)
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        access_token = create_access_token({
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user["role"]
        })
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user"""
    return {"message": "Successfully logged out"}



@router.delete("/delete-account")
async def delete_my_account(
    delete_request: DeleteAccountRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Delete your own account and all associated data.
    Requires password and typing 'DELETE' for confirmation.
    """
    try:
        user_model = User(db)
        
        # Verify password
        if not user_model.verify_password(delete_request.password, current_user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        # Verify confirmation text
        if delete_request.confirmation != "DELETE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Please type "DELETE" to confirm account deletion'
            )
        
        # Prevent admin self-deletion (use admin endpoint instead)
        if current_user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin accounts cannot be deleted through this endpoint. Contact another administrator."
            )
        
        user_id = str(current_user["_id"])
        user_email = current_user["email"]
        
        # Cascading delete - remove all user data
        # 1. Delete wallet
        wallet_result = await db.wallets.delete_one({"user_id": ObjectId(user_id)})
        
        # 2. Delete face data
        face_result = await db.face_data.delete_many({"user_id": ObjectId(user_id)})
        
        # 3. Delete journeys
        journey_result = await db.journeys.delete_many({"user_id": ObjectId(user_id)})
        
        # 4. Delete user account
        user_result = await db.users.delete_one({"_id": ObjectId(user_id)})
        
        logger.info(f"User self-deleted account: {user_email} (ID: {user_id})")
        
        return {
            "success": True,
            "message": "Account deleted successfully. All your data has been permanently removed.",
            "deleted_data": {
                "user": True,
                "wallet": wallet_result.deleted_count > 0,
                "face_data": face_result.deleted_count,
                "journeys": journey_result.deleted_count
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Self-delete account failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account"
        )










# from fastapi import APIRouter, Depends, HTTPException, status
# from app.core.database import get_database
# from app.core.security import create_tokens, get_current_user, verify_token
# from app.models.user import User
# from app.models.wallet import Wallet   # ✅ added import
# from app.schemas.auth import (
#     UserRegistration, 
#     UserLogin, 
#     AdminLogin,
#     TokenResponse, 
#     UserResponse, 
#     ChangePassword
# )
# from datetime import timedelta
# from app.core.config import settings
# import logging

# logger = logging.getLogger(__name__)
# router = APIRouter()


# @router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
# async def register_user(
#     user_data: UserRegistration,
#     db = Depends(get_database)
# ):
#     """Register new user with automatic wallet creation"""
#     try:
#         user_model = User(db)
        
#         # Prepare user data
#         user_dict = {
#             "email": user_data.email,
#             "password": user_data.password,
#             "first_name": user_data.first_name,
#             "last_name": user_data.last_name,
#             "phone": user_data.phone,
#             "date_of_birth": user_data.date_of_birth,
#             "role": "user"
#         }
        
#         # Create user
#         created_user = await user_model.create_user(user_dict)
#         user_id = str(created_user["_id"])
        
#         # 🔥 AUTO-CREATE WALLET for the new user
#         wallet_model = Wallet(db)
#         wallet = await wallet_model.create_wallet_for_user(user_id)
        
#         logger.info(f"✅ User registered with wallet: {user_id}")
        
#         # Generate tokens
#         tokens = create_tokens(created_user)
        
#         # Prepare response with wallet info
#         user_response = UserResponse(
#             id=user_id,
#             email=created_user["email"],
#             first_name=created_user["first_name"],
#             last_name=created_user["last_name"],
#             phone=created_user["phone"],
#             date_of_birth=created_user["date_of_birth"],
#             role=created_user["role"],
#             wallet_balance=float(wallet["balance"]),  # ✅ wallet balance from Wallet model
#             is_active=created_user["is_active"],
#             created_at=created_user["created_at"],
#             last_login=created_user.get("last_login")
#         )
        
#         return TokenResponse(
#             access_token=tokens["access_token"],
#             refresh_token=tokens["refresh_token"],
#             token_type=tokens["token_type"],
#             user=user_response
#         )
        
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"User registration failed: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Registration failed"
#         )


# @router.post("/login", response_model=TokenResponse)
# async def login_user(login_data: UserLogin, db = Depends(get_database)):
#     """User login"""
#     try:
#         user_model = User(db)
#         user = await user_model.authenticate_user(login_data.email, login_data.password)
#         if not user:
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
#         tokens = create_tokens(user)
#         user_response = UserResponse(
#             id=str(user["_id"]),
#             email=user["email"],
#             first_name=user["first_name"],
#             last_name=user["last_name"],
#             phone=user["phone"],
#             date_of_birth=user["date_of_birth"],
#             role=user["role"],
#             wallet_balance=user["wallet_balance"],
#             is_active=user["is_active"],
#             created_at=user["created_at"],
#             last_login=user.get("last_login")
#         )
#         return TokenResponse(
#             access_token=tokens["access_token"],
#             refresh_token=tokens["refresh_token"],
#             token_type=tokens["token_type"],
#             user=user_response
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"User login failed: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed")


# @router.post("/admin/login", response_model=TokenResponse)
# async def admin_login(login_data: AdminLogin, db = Depends(get_database)):
#     """Admin login"""
#     try:
#         user_model = User(db)
#         user = await user_model.authenticate_user(login_data.email, login_data.password)
#         if not user or user.get("role") != "admin":
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")
#         tokens = create_tokens(user)
#         user_response = UserResponse(
#             id=str(user["_id"]),
#             email=user["email"],
#             first_name=user["first_name"],
#             last_name=user["last_name"],
#             phone=user["phone"],
#             date_of_birth=user["date_of_birth"],
#             role=user["role"],
#             wallet_balance=user["wallet_balance"],
#             is_active=user["is_active"],
#             created_at=user["created_at"],
#             last_login=user.get("last_login")
#         )
#         return TokenResponse(
#             access_token=tokens["access_token"],
#             refresh_token=tokens["refresh_token"],
#             token_type=tokens["token_type"],
#             user=user_response
#         )
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Admin login failed: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Admin login failed")


# @router.get("/profile", response_model=UserResponse)
# async def get_user_profile(current_user: dict = Depends(get_current_user)):
#     """Get current user profile"""
#     return UserResponse(
#         id=current_user["_id"],
#         email=current_user["email"],
#         first_name=current_user["first_name"],
#         last_name=current_user["last_name"],
#         phone=current_user["phone"],
#         date_of_birth=current_user["date_of_birth"],
#         role=current_user["role"],
#         wallet_balance=current_user["wallet_balance"],
#         is_active=current_user["is_active"],
#         created_at=current_user["created_at"],
#         last_login=current_user.get("last_login")
#     )


# @router.put("/change-password")
# async def change_password(password_data: ChangePassword, current_user: dict = Depends(get_current_user), db = Depends(get_database)):
#     """Change user password"""
#     try:
#         user_model = User(db)
#         authenticated_user = await user_model.authenticate_user(current_user["email"], password_data.current_password)
#         if not authenticated_user:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
#         await user_model.update_user(current_user["_id"], {"password": password_data.new_password})
#         return {"message": "Password changed successfully"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Password change failed: {e}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Password change failed")


# @router.post("/refresh")
# async def refresh_access_token(refresh_token: str):
#     """Refresh access token"""
#     try:
#         payload = verify_token(refresh_token)
#         if payload is None or payload.get("type") != "refresh":
#             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
#         from app.core.security import create_access_token
#         access_token = create_access_token(
#             data={"sub": payload["sub"], "email": payload["email"], "role": payload["role"]},
#             expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#         )
#         return {"access_token": access_token, "token_type": "bearer"}
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Token refresh failed: {e}")
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token refresh failed")


# @router.post("/logout")
# async def logout(current_user: dict = Depends(get_current_user)):
#     """Logout user"""
#     return {"message": "Successfully logged out"}

















