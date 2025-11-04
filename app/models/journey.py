from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging
import uuid

from app.core.utils import convert_decimals_to_bson  # ✅ Import utility

logger = logging.getLogger(__name__)

class Journey:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.journeys

    async def start_journey(self, user_id: str, entry_station_id: str, entry_station_code: str) -> Dict:
        """Start new journey when user face is recognized at entry"""
        try:
            # Check if user has ongoing journey
            ongoing = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "status": "ongoing",
                "is_active": True
            })

            if ongoing is not None:
                raise ValueError("User has ongoing journey. Must exit first.")

            journey_id = f"JRN{int(datetime.utcnow().timestamp())}{str(uuid.uuid4())[-4:].upper()}"

            journey = {
                "journey_id": journey_id,
                "user_id": ObjectId(user_id),
                "entry_station_id": ObjectId(entry_station_id),
                "entry_station_code": entry_station_code.upper(),
                "entry_time": datetime.utcnow(),
                "exit_station_id": None,
                "exit_station_code": None,
                "exit_time": None,
                "journey_duration_minutes": None,
                "fare_details": {
                    "base_fare": None,
                    "tax_amount": None,
                    "service_charge": None,
                    "total_fare": None,
                    "is_peak_hour": False,
                    "penalty_fare": 0.0
                },
                "status": "ongoing",
                "max_journey_time": datetime.utcnow() + timedelta(hours=4),  # 4-hour limit
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            result = await self.collection.insert_one(journey)
            journey["_id"] = str(result.inserted_id)
            journey["user_id"] = str(journey["user_id"])
            journey["entry_station_id"] = str(journey["entry_station_id"])

            logger.info(f"✅ Journey started: {journey_id} at {entry_station_code}")
            return journey

        except Exception as e:
            logger.error(f"❌ Start journey failed: {e}")
            raise

    async def complete_journey(self, user_id: str, exit_station_id: str, exit_station_code: str, fare_calculation: Dict) -> Dict:
        """Complete journey when user exits - Simplified (no tax)"""
        try:
            journey = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "status": "ongoing",
                "is_active": True
            })
            
            if journey is None:
                raise ValueError("No ongoing journey found for user")
            
            exit_time = datetime.utcnow()
            journey_duration = exit_time - journey["entry_time"]
            
            # Check if journey exceeded max time (4 hours)
            if exit_time > journey["max_journey_time"]:
                penalty_fare = 50.0
                total_fare = float(fare_calculation["total_fare"]) + penalty_fare
                fare_calculation["penalty_fare"] = penalty_fare
                fare_calculation["total_fare"] = total_fare
            
            # ✅ FIX: Only use simplified fare fields (no tax_amount, no service_charge separately)
            update_data = {
                "exit_station_id": ObjectId(exit_station_id),
                "exit_station_code": exit_station_code.upper(),
                "exit_time": exit_time,
                "journey_duration_minutes": int(journey_duration.total_seconds() / 60),
                "fare_details": {
                    "from_station": fare_calculation.get("from_station"),
                    "to_station": fare_calculation.get("to_station"),
                    "distance_km": fare_calculation.get("distance_km"),
                    "base_fare": float(fare_calculation.get("base_fare", 0)),
                    "service_charge": float(fare_calculation.get("service_charge", 0)),
                    "total_fare": float(fare_calculation.get("total_fare", 0)),
                    "penalty_fare": float(fare_calculation.get("penalty_fare", 0))
                },
                "status": "completed",
                "is_peak_hour": fare_calculation.get("is_peak_hour", False),
                "updated_at": exit_time
            }
            
            # Convert to BSON-safe values
            update_data = convert_decimals_to_bson(update_data)
            
            await self.collection.update_one(
                {"_id": journey["_id"]},
                {"$set": update_data}
            )
            
            completed_journey = await self.collection.find_one({"_id": journey["_id"]})
            
            # Convert ObjectIds to strings
            completed_journey["_id"] = str(completed_journey["_id"])
            completed_journey["user_id"] = str(completed_journey["user_id"])
            completed_journey["entry_station_id"] = str(completed_journey["entry_station_id"])
            completed_journey["exit_station_id"] = str(completed_journey["exit_station_id"])
            
            logger.info(f"Journey completed: {journey['journey_id']} - Fare: ₹{fare_calculation['total_fare']}")
            return completed_journey
            
        except Exception as e:
            logger.error(f"Complete journey failed: {e}")
            raise


    async def get_ongoing_journey(self, user_id: str) -> Optional[Dict]:
        """Get user's current ongoing journey"""
        try:
            journey = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "status": "ongoing",
                "is_active": True
            })

            if journey is not None:
                journey["_id"] = str(journey["_id"])
                journey["user_id"] = str(journey["user_id"])
                journey["entry_station_id"] = str(journey["entry_station_id"])
                if journey["exit_station_id"]:
                    journey["exit_station_id"] = str(journey["exit_station_id"])

            return journey

        except Exception as e:
            logger.error(f"❌ Get ongoing journey failed: {e}")
            return None

    async def get_user_journey_history(self, user_id: str, skip: int = 0, limit: int = 50) -> list:
        """Get user's completed journey history"""
        try:
            cursor = self.collection.find({
                "user_id": ObjectId(user_id),
                "status": "completed",
                "is_active": True
            }).sort("exit_time", -1).skip(skip).limit(limit)

            journeys = []
            async for journey in cursor:
                journey["_id"] = str(journey["_id"])
                journey["user_id"] = str(journey["user_id"])
                journey["entry_station_id"] = str(journey["entry_station_id"])
                journey["exit_station_id"] = str(journey["exit_station_id"])
                journeys.append(journey)

            return journeys

        except Exception as e:
            logger.error(f"❌ Get journey history failed: {e}")
            return []


