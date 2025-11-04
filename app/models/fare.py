from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import Dict, Optional,List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ✅ Utility function to safely convert Decimals to floats
def convert_decimals_to_bson(data):
    if isinstance(data, dict):
        return {k: convert_decimals_to_bson(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimals_to_bson(v) for v in data]
    elif isinstance(data, float) or isinstance(data, int) or isinstance(data, str):
        return data
    elif hasattr(data, "quantize"):  # Decimal
        return float(data)
    return data


class Fare:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.fares
        
    async def create_fare(self, fare_data: Dict) -> Dict:
        """Create or update fare between stations - Simplified"""
        try:
            fare_update = {
                "from_station_id": ObjectId(fare_data["from_station_id"]),
                "to_station_id": ObjectId(fare_data["to_station_id"]),
                "from_station_code": fare_data["from_station_code"].upper(),
                "to_station_code": fare_data["to_station_code"].upper(),
                "distance_km": fare_data["distance_km"],
                "base_fare": float(fare_data["base_fare"]),
                "is_active": True,
                "updated_at": datetime.utcnow()
            }
            
            # Check if fare already exists
            existing = await self.collection.find_one({
                "from_station_id": fare_update["from_station_id"],
                "to_station_id": fare_update["to_station_id"]
            })
            
            if existing:
                # ✅ Update existing fare
                result = await self.collection.find_one_and_update(
                    {"_id": existing["_id"]},
                    {"$set": fare_update},
                    return_document=True
                )
                logger.info(f"Fare updated: {fare_update['from_station_code']} → {fare_update['to_station_code']}")
            else:
                # ✅ Create new fare
                fare_update["created_at"] = datetime.utcnow()
                result = await self.collection.insert_one(fare_update)
                fare_update["_id"] = result.inserted_id
                result = fare_update
                logger.info(f"Fare created: {fare_update['from_station_code']} → {fare_update['to_station_code']}")
            
            # Convert ObjectIds to strings for response
            result["_id"] = str(result["_id"])
            result["from_station_id"] = str(result["from_station_id"])
            result["to_station_id"] = str(result["to_station_id"])
            
            return result
            
        except Exception as e:
            logger.error(f"Fare creation/update failed: {e}")
            raise

    
    async def get_fare(self, from_station_id: str, to_station_id: str) -> Optional[Dict]:
        """Get fare between two stations"""
        try:
            fare = await self.collection.find_one({
                "from_station_id": ObjectId(from_station_id),
                "to_station_id": ObjectId(to_station_id),
                "is_active": True
            })
            
            if fare is not None:
                fare["_id"] = str(fare["_id"])
                fare["from_station_id"] = str(fare["from_station_id"])
                fare["to_station_id"] = str(fare["to_station_id"])
                fare["base_fare"] = float(fare["base_fare"])
                fare["express_fare"] = float(fare["express_fare"])
                
            return fare
            
        except Exception as e:
            logger.error(f"❌ Get fare failed: {e}")
            return None
    async def calculate_fare(self, from_station_code: str, to_station_code: str) -> Dict:
        """Calculate fare - Bidirectional (works both ways) - Simplified"""
        try:
            # Try forward direction (A → B)
            fare = await self.collection.find_one({
                "from_station_code": from_station_code.upper(),
                "to_station_code": to_station_code.upper(),
                "is_active": True
            })
            
            # If not found, try reverse direction (B → A)
            if fare is None:
                fare = await self.collection.find_one({
                    "from_station_code": to_station_code.upper(),  # ✅ Swapped
                    "to_station_code": from_station_code.upper(),  # ✅ Swapped
                    "is_active": True
                })
            
            if fare is None:
                raise ValueError(f"No fare found for route {from_station_code} ↔ {to_station_code}")
            
            # ✅ Simple calculation - Base Fare + ₹5 Service Charge
            base_fare = float(fare["base_fare"])
            service_charge = 5.0  # Fixed ₹5
            total_fare = base_fare + service_charge
            
            return {
                "from_station": from_station_code.upper(),
                "to_station": to_station_code.upper(),
                "distance_km": fare["distance_km"],
                "base_fare": base_fare,
                "service_charge": service_charge,
                "total_fare": round(total_fare, 2)
            }
            
        except Exception as e:
            logger.error(f"Calculate fare failed: {e}")
            raise



    async def get_all_fares(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """Get all active fares with pagination"""
        try:
            cursor = self.collection.find({"is_active": True}) \
                .sort("from_station_code", 1) \
                .skip(skip) \
                .limit(limit)
            
            fares = []
            async for fare in cursor:
                fare["_id"] = str(fare["_id"])
                fare["from_station_id"] = str(fare["from_station_id"])
                fare["to_station_id"] = str(fare["to_station_id"])
                fares.append(fare)
            
            return fares
            
        except Exception as e:
            logger.error(f"Get all fares failed: {e}")
            return []













