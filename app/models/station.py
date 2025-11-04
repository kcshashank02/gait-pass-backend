from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Station:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.stations
        
    async def create_station(self, station_data: Dict) -> Dict:
        """Create new station with simplified schema"""
        try:
            station = {
                "station_code": station_data["station_code"].upper(),
                "station_name": station_data["station_name"],
                "city": station_data["city"],
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Check if station code already exists
            existing = await self.collection.find_one({"station_code": station["station_code"]})
            if existing is not None:
                raise ValueError(f"Station with code {station['station_code']} already exists")
            
            result = await self.collection.insert_one(station)
            station["_id"] = str(result.inserted_id)
            logger.info(f"Station created: {station['station_code']}")
            return station
            
        except Exception as e:
            logger.error(f"Station creation failed: {e}")
            raise

    
    async def get_all_stations(self, skip: int = 0, limit: int = 100) -> List[Dict]:
        """Get all active stations"""
        try:
            cursor = self.collection.find(
                {"is_active": True}
            ).skip(skip).limit(limit).sort("station_name", 1)
            
            stations = []
            async for station in cursor:
                station["_id"] = str(station["_id"])
                stations.append(station)
            
            return stations
            
        except Exception as e:
            logger.error(f"❌ Get stations failed: {e}")
            return []
    
    async def get_station_by_id(self, station_id: str) -> Optional[Dict]:
        """Get station by ID"""
        try:
            station = await self.collection.find_one({
                "_id": ObjectId(station_id),
                "is_active": True
            })
            
            if station is not None:
                station["_id"] = str(station["_id"])
                
            return station
            
        except Exception as e:
            logger.error(f"❌ Get station failed: {e}")
            return None
    
    async def get_station_by_code(self, station_code: str) -> Optional[Dict]:
        """Get station by station code"""
        try:
            station = await self.collection.find_one({
                "station_code": station_code.upper(),
                "is_active": True
            })
            
            if station is not None:
                station["_id"] = str(station["_id"])
                
            return station
            
        except Exception as e:
            logger.error(f"❌ Get station by code failed: {e}")
            return None
    async def update_station(self, station_id: str, update_data: Dict) -> Optional[Dict]:
        """Update station details"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(station_id)},
                {"$set": update_data},
                return_document=True
            )
            if result is not None:
                result["_id"] = str(result["_id"])
            return result
        except Exception as e:
            logger.error(f"Station update failed: {e}")
            return None

    
    async def delete_station(self, station_id: str) -> bool:
        """Soft delete station"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(station_id)},
                {
                    "$set": {
                        "is_active": False,
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Station deletion failed: {e}")
            return False
    
    async def search_stations(self, query: str) -> List[Dict]:
        """Search stations by name or city"""
        try:
            cursor = self.collection.find({
                "is_active": True,
                "$or": [
                    {"station_name": {"$regex": query, "$options": "i"}},
                    {"city": {"$regex": query, "$options": "i"}},
                    {"station_code": {"$regex": query.upper(), "$options": "i"}}
                ]
            }).limit(20)
            
            stations = []
            async for station in cursor:
                station["_id"] = str(station["_id"])
                stations.append(station)
            
            return stations
            
        except Exception as e:
            logger.error(f"❌ Station search failed: {e}")
            return []
