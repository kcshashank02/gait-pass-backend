from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Dict, Optional
from datetime import datetime
from pymongo import ReturnDocument
import logging

from app.core.utils import convert_decimals_to_bson  # ✅ Import utility

logger = logging.getLogger(__name__)

class Wallet:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.wallets

    async def create_wallet_for_user(self, user_id: str) -> Dict:
        """Create wallet automatically when user registers"""
        try:
            # Check if wallet already exists
            existing_wallet = await self.collection.find_one({"user_id": ObjectId(user_id)})
            if existing_wallet is not None:
                return existing_wallet

            # Create new wallet with float instead of Decimal
            wallet_data = {
                "user_id": ObjectId(user_id),
                "balance": 0.0,  # ✅ Use float
                "status": "inactive",
                "currency": "INR",
                "wallet_number": f"WAL{str(ObjectId())[-8:].upper()}",
                "transactions": [],
                "payment_methods": [],
                "limits": {
                    "daily_limit": 10000.0,      # ✅ Use float
                    "monthly_limit": 50000.0,    # ✅ Use float
                    "single_transaction_limit": 5000.0  # ✅ Use float
                },
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "is_active": True
            }

            # Ensure MongoDB-safe types
            wallet_data = convert_decimals_to_bson(wallet_data)

            result = await self.collection.insert_one(wallet_data)
            wallet_data["_id"] = result.inserted_id
            wallet_data["user_id"] = str(wallet_data["user_id"])

            logger.info(f"✅ Wallet created for user {user_id}")
            return wallet_data

        except Exception as e:
            logger.error(f"❌ Wallet creation failed for user {user_id}: {e}")
            raise

    async def activate_wallet(self, user_id: str) -> Dict:
        """Activate user's wallet"""
        try:
            wallet = await self.collection.find_one_and_update(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "status": "active",
                        "activated_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                },
                return_document=ReturnDocument.AFTER
            )

            if wallet is None:
                raise ValueError("Wallet not found")

            wallet["_id"] = str(wallet["_id"])
            wallet["user_id"] = str(wallet["user_id"])

            logger.info(f"✅ Wallet activated for user {user_id}")
            return wallet

        except Exception as e:
            logger.error(f"❌ Wallet activation failed for user {user_id}: {e}")
            raise

    async def get_wallet_by_user_id(self, user_id: str) -> Optional[Dict]:
        """Get wallet details for user"""
        try:
            wallet = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "is_active": True
            })

            if wallet is not None:
                wallet["_id"] = str(wallet["_id"])
                wallet["user_id"] = str(wallet["user_id"])
                wallet["balance"] = float(wallet["balance"])  # ✅ Ensure float

                # Convert transaction amounts
                for transaction in wallet.get("transactions", []):
                    transaction["amount"] = float(transaction["amount"])

            return wallet

        except Exception as e:
            logger.error(f"❌ Get wallet failed for user {user_id}: {e}")
            return None

    async def add_transaction(self, user_id: str, transaction_data: Dict) -> bool:
        """Add transaction to wallet history"""
        try:
            transaction = {
                "transaction_id": str(ObjectId()),
                "type": transaction_data["type"],  # "credit" or "debit"
                "amount": float(transaction_data["amount"]),  # ✅ Use float
                "description": transaction_data.get("description", ""),
                "reference": transaction_data.get("reference", ""),
                "timestamp": datetime.utcnow(),
                "status": "completed"
            }

            # Update balance
            balance_update = float(transaction_data["amount"])
            if transaction_data["type"] == "debit":
                balance_update = -balance_update

            result = await self.collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$inc": {"balance": balance_update},
                    "$push": {"transactions": transaction},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"❌ Add transaction failed for user {user_id}: {e}")
            return False

    async def get_balance(self, user_id: str) -> float:
        """Get current wallet balance"""
        try:
            wallet = await self.collection.find_one(
                {"user_id": ObjectId(user_id), "is_active": True},
                {"balance": 1}
            )

            if wallet is None:
                return 0.0

            return float(wallet["balance"])

        except Exception as e:
            logger.error(f"❌ Get balance failed for user {user_id}: {e}")
            return 0.0

    async def check_sufficient_balance(self, user_id: str, amount: float) -> bool:
        """Check if user has sufficient balance"""
        current_balance = await self.get_balance(user_id)
        return current_balance >= amount









