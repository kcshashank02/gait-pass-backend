from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime

from app.core.database import get_database
from app.core.security import get_current_user, get_current_admin_user
from app.models.wallet import Wallet

router = APIRouter()

class WalletActivationRequest(BaseModel):
    user_id: str

class RechargeRequest(BaseModel):
    amount: float
    payment_method: str  # "card", "upi", "netbanking"
    reference: Optional[str] = None
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 10000:  # Daily limit
            raise ValueError('Amount exceeds daily limit of ₹10,000')
        return v

class TransferRequest(BaseModel):
    to_user_id: str
    amount: float
    description: Optional[str] = "Money transfer"
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v

class WalletResponse(BaseModel):
    user_id: str
    balance: float
    status: str
    wallet_number: str
    currency: str
    created_at: datetime
    activated_at: Optional[datetime] = None

@router.post("/activate")
async def activate_wallet(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Activate user's wallet"""
    try:
        wallet_model = Wallet(db)
        wallet = await wallet_model.activate_wallet(current_user["_id"])
        
        return {
            "success": True,
            "message": "Wallet activated successfully",
            "wallet": WalletResponse(
                user_id=wallet["user_id"],
                balance=float(wallet["balance"]),
                status=wallet["status"],
                wallet_number=wallet["wallet_number"],
                currency=wallet["currency"],
                created_at=wallet["created_at"],
                activated_at=wallet.get("activated_at")
            )
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wallet activation failed: {str(e)}"
        )

@router.get("/balance")
async def get_wallet_balance(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get current wallet balance"""
    try:
        wallet_model = Wallet(db)
        balance = await wallet_model.get_balance(current_user["_id"])
        
        return {
            "user_id": current_user["_id"],
            "balance": balance,
            "currency": "INR"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get balance: {str(e)}"
        )

@router.get("/details")
async def get_wallet_details(
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get complete wallet details"""
    try:
        wallet_model = Wallet(db)
        wallet = await wallet_model.get_wallet_by_user_id(current_user["_id"])
        
        if wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        return {
            "success": True,
            "wallet": wallet
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet details: {str(e)}"
        )

@router.post("/recharge")
async def recharge_wallet(
    recharge_data: RechargeRequest,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Add money to wallet"""
    try:
        wallet_model = Wallet(db)
        
        # Add credit transaction
        transaction_data = {
            "type": "credit",
            "amount": recharge_data.amount,
            "description": f"Wallet recharge via {recharge_data.payment_method}",
            "reference": recharge_data.reference or f"RECHARGE_{int(datetime.utcnow().timestamp())}"
        }
        
        success = await wallet_model.add_transaction(current_user["_id"], transaction_data)
        
        if success:
            # Get updated balance
            new_balance = await wallet_model.get_balance(current_user["_id"])
            
            return {
                "success": True,
                "message": "Wallet recharged successfully",
                "amount": recharge_data.amount,
                "new_balance": new_balance,
                "transaction_reference": transaction_data["reference"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Recharge transaction failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recharge failed: {str(e)}"
        )

@router.get("/history")
async def get_transaction_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db = Depends(get_database)
):
    """Get wallet transaction history"""
    try:
        wallet_model = Wallet(db)
        wallet = await wallet_model.get_wallet_by_user_id(current_user["_id"])
        
        if wallet is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wallet not found"
            )
        
        # Get recent transactions (limit to prevent large responses)
        transactions = wallet.get("transactions", [])
        recent_transactions = sorted(transactions, key=lambda x: x["timestamp"], reverse=True)[:limit]
        
        return {
            "success": True,
            "user_id": current_user["_id"],
            "transactions": recent_transactions,
            "total_transactions": len(transactions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get transaction history: {str(e)}"
        )

# Admin endpoints
@router.get("/admin/all")
async def get_all_wallets(
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Get all wallets (admin only)"""
    try:
        cursor = db.wallets.find({"is_active": True}).skip(skip).limit(limit)
        
        wallets = []
        async for wallet in cursor:
            wallet["_id"] = str(wallet["_id"])
            wallet["user_id"] = str(wallet["user_id"])
            wallet["balance"] = float(wallet["balance"])
            wallets.append(wallet)
        
        total_count = await db.wallets.count_documents({"is_active": True})
        
        return {
            "success": True,
            "wallets": wallets,
            "total": total_count,
            "page": skip // limit + 1
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallets: {str(e)}"
        )


@router.get("/transactions")
async def get_transaction_history(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get user's transaction history"""
    try:
        wallet_model = Wallet(db)
        
        # Get user's wallet
        wallet = await wallet_model.get_wallet_by_user_id(str(current_user["_id"]))
        
        if not wallet:
            return {
                "success": True,
                "transactions": [],
                "total": 0,
                "skip": skip,
                "limit": limit
            }
        
        # Get transactions from wallet
        all_transactions = wallet.get("transactions", [])
        
        # Pagination
        total = len(all_transactions)
        transactions = all_transactions[skip : skip + limit]
        
        return {
            "success": True,
            "transactions": transactions,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Get transactions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transactions"
        )

    