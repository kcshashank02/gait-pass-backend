from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from typing import List, Dict, Optional
from datetime import datetime
import logging
import numpy as np

logger = logging.getLogger(__name__)

class FaceData:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db.face_data
        
    async def store_embedding_only(
        self,
        user_id: str,
        person_name: str,
        face_embedding: List[float],
        confidence: float = 0.85,
        sample_count: int = 1
    ) -> Dict:
        """Store ONLY face embedding - NO images saved"""
        try:
            face_data = {
                "user_id": ObjectId(user_id),
                "person_name": person_name,
                "face_embedding": face_embedding,  # 512 floats (~2KB)
                "confidence": confidence,
                "registration_metadata": {
                    "sample_count": sample_count,
                    "method": "embeddings_only",
                    "model": "insightface_arcface",
                    "dimensions": len(face_embedding),
                    "registered_at": datetime.utcnow()
                },
                "recognition_stats": {
                    "total_recognitions": 0,
                    "last_recognized": None,
                    "average_confidence": 0.0,
                    "history": []
                },
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Replace any existing face data for this user
            await self.collection.replace_one(
                {"user_id": ObjectId(user_id)},
                face_data,
                upsert=True
            )
            
            # Return stored document
            doc = await self.collection.find_one({"user_id": ObjectId(user_id)})
            if doc is not None:
                doc["_id"] = str(doc["_id"])
                doc["user_id"] = str(doc["user_id"])
            
            logger.info(f"✅ Face embedding stored for user {user_id} - {len(face_embedding)} dimensions")
            return doc
            
        except Exception as e:
            logger.error(f"❌ Face embedding storage failed: {e}")
            raise
    
    async def get_embedding(self, user_id: str) -> Optional[List[float]]:
        """Get face embedding for user"""
        try:
            doc = await self.collection.find_one({
                "user_id": ObjectId(user_id),
                "is_active": True
            })
            
            if doc is not None:
                return doc.get("face_embedding", [])
            return None
            
        except Exception as e:
            logger.error(f"Get embedding failed: {e}")
            return None
    
    async def get_all_active_embeddings(self) -> Dict[str, List[List[float]]]:
        """Get all active face embeddings grouped by user_id"""
        try:
            cursor = self.collection.find(
                {"is_active": True},
                {"user_id": 1, "face_embedding": 1}  # ✅ Correct field name
            )
        
            embeddings_dict = {}
            async for doc in cursor:
                user_id = str(doc["user_id"])
                embedding = doc.get("face_embedding")  # ✅ Singular, not plural
            
            if embedding:
                if user_id not in embeddings_dict:
                    embeddings_dict[user_id] = []
                embeddings_dict[user_id].append(embedding)
        
            return embeddings_dict
        
        except Exception as e:
            logger.error(f"Failed to get all embeddings: {e}")
            return {}

    
    async def update_recognition_stats(self, user_id: str, confidence: float, location: str):
        """Update recognition statistics"""
        try:
            await self.collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$inc": {"recognition_stats.total_recognitions": 1},
                    "$set": {
                        "recognition_stats.last_recognized": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    },
                    "$push": {
                        "recognition_stats.history": {
                            "$each": [{
                                "timestamp": datetime.utcnow(),
                                "confidence": confidence,
                                "location": location
                            }],
                            "$slice": -50  # Keep only last 50 recognition events
                        }
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Update recognition stats failed: {e}")
    
    async def delete_embedding(self, user_id: str) -> bool:
        """Soft delete face embedding"""
        try:
            result = await self.collection.update_one(
                {"user_id": ObjectId(user_id)},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Delete embedding failed: {e}")
            return False






