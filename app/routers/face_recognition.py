from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from typing import List, Optional, Literal, Dict, Union
import httpx
import os
from app.core.config import settings 
import numpy as np
from datetime import datetime

from app.core.database import get_database
from app.core.security import get_current_user, get_current_admin_user  # ✅ Import admin auth
from app.models.face_data import FaceData
from app.models.user import User
import logging


logger = logging.getLogger(__name__) 
router = APIRouter()

# ✅ ML Service URL (from environment)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:7860")


# ---------------------------------------------------------------------------
# ✅ Register Face - Embeddings Only (calls ML microservice)
# ---------------------------------------------------------------------------
@router.post("/register-embedding-only")
async def register_face_embedding_only(
    user_id: str = Form(...),
    person_name: str = Form(...),
    registration_type: Literal["file_upload", "camera_capture"] = Form(...),
    images: Optional[Union[UploadFile, List[UploadFile]]] = File(None),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Register user face - extract embeddings via external ML service (no image storage)."""

    if images and not isinstance(images, list):
        images = [images]

    # Permission check
    if current_user["role"] != "admin" and current_user["_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # User check
    user_model = User(db)
    user = await user_model.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    embeddings = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for image in images:
                files = {"image": (image.filename, await image.read(), image.content_type)}
                response = await client.post(f"{ML_SERVICE_URL}/extract-embedding", files=files)

                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        embeddings.append(result["embedding"])

        if not embeddings:
            raise HTTPException(status_code=400, detail="No faces detected")

        # Compute average embedding
        avg_embedding = np.mean(embeddings, axis=0).tolist()
        confidence = 0.85 + (len(embeddings) * 0.02)

        # Store embedding only
        face_data_model = FaceData(db)
        face_data = await face_data_model.store_embedding_only(
            user_id=user_id,
            person_name=person_name,
            face_embedding=avg_embedding,
            confidence=min(confidence, 0.98),
            sample_count=len(embeddings)
        )

        return {
            "success": True,
            "message": "Face registered successfully (embeddings only)",
            "face_data_id": face_data["_id"],
            "images_processed": len(embeddings)
        }

    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# ✅ Test Face Recognition (No Authentication Required)
# # ---------------------------------------------------------------------------
# @router.post("/test-face-recognition")
# async def test_face_recognition(
#     frame: UploadFile = File(...),
#     db=Depends(get_database)
# ):
#     """Test face recognition - For users to verify their registered face"""
#     try:
#         # Read image
#         image_bytes = await frame.read()
        
#         # Call ML service to extract embedding
#         ml_service_url = settings.ML_SERVICE_URL
#         files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        
#         async with httpx.AsyncClient(timeout=30.0) as client:
#             response = await client.post(
#                 f"{ml_service_url}/extract-embedding",
#                 files=files
#             )
        
#         if response.status_code != 200:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="ML service failed to extract embedding"
#             )
        
#         ml_response = response.json()
#         query_embedding = ml_response.get("embedding")
        
#         if not query_embedding:
#             return {
#                 "recognized": False,
#                 "message": "No face detected in image"
#             }
        
#         # Get all registered faces from database
#         face_data_model = FaceData(db)
#         all_embeddings = await face_data_model.get_all_active_embeddings()
        
#         if not all_embeddings:
#             return {
#                 "recognized": False,
#                 "message": "No registered faces in system"
#             }
        
#         # all_embeddings is already in correct format: {user_id: [embedding]}
#         known_faces = all_embeddings
        
#         # Call ML service for batch recognition
#         async with httpx.AsyncClient(timeout=30.0) as client:
#             response = await client.post(
#                 f"{ml_service_url}/batch-recognize",
#                 json={
#                     "query_embedding": query_embedding,
#                     "known_faces": known_faces,
#                     "threshold": 0.7
#                 }
#             )
        
#         if response.status_code != 200:
#             raise HTTPException(
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 detail="Face recognition failed"
#             )
        
#         result = response.json()
        
#         if result.get("recognized"):
#             # Get user details
#             user_model = User(db)
#             user = await user_model.get_user_by_id(result["user_id"])
            
#             return {
#                 "recognized": True,
#                 "user_id": result["user_id"],
#                 "user_name": f"{user['first_name']} {user['last_name']}" if user else "Unknown",
#                 "email": user["email"] if user else None,
#                 "confidence": result.get("confidence", 0.0),
#                 "match_score": result.get("min_distance", 0.0)
#             }
#         else:
#             return {
#                 "recognized": False,
#                 "message": "Face not recognized. Please register your face first."
#             }
            
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Test face recognition failed: {e}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Face recognition test failed: {str(e)}"
#         )






@router.post("/test-face-recognition")
async def test_face_recognition(
    frame: UploadFile = File(...),
    db=Depends(get_database)
):
    """
    Test face recognition - Verify registered face
    """
    try:
        logger.info("Starting face recognition test...")
        
        # Read image
        image_bytes = await frame.read()
        logger.info(f"Image received: {len(image_bytes)} bytes")
        
        # Extract embedding from image
        ml_service_url = settings.ML_SERVICE_URL
        files = {"image": ("frame.jpg", image_bytes, "image/jpeg")}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ml_service_url}/extract-embedding",
                files=files
            )
            
            if response.status_code != 200:
                logger.error(f"ML service error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "recognized": False,
                    "message": f"ML service error: {response.text}"
                }
            
            ml_response = response.json()
            logger.info(f"ML response: {ml_response}")
            
            if not ml_response.get("success"):
                return {
                    "success": False,
                    "recognized": False,
                    "message": ml_response.get("message", "Face extraction failed")
                }
            
            query_embedding = ml_response.get("embedding")
            
            if not query_embedding:
                return {
                    "success": False,
                    "recognized": False,
                    "message": "No face detected in image"
                }
            
        
        # Get all registered faces
        facedata_model = FaceData(db)
        all_embeddings = await facedata_model.get_all_active_embeddings()
        
        logger.info(f"Found {len(all_embeddings)} registered faces")
        logger.info(f"Known faces format: {list(all_embeddings.keys())[:3] if all_embeddings else []}")
        
        if not all_embeddings:
            return {
                "success": True,
                "recognized": False,
                "message": "No registered faces in system"
            }
        
        # ✅ FIX: Ensure known_faces format is correct {user_id: [embedding]}
        # Check if embeddings are already in correct format
        known_faces = {}
        for user_id, embedding_data in all_embeddings.items():
            # Handle both formats: direct list or nested dict
            if isinstance(embedding_data, list):
                known_faces[user_id] = embedding_data
            elif isinstance(embedding_data, dict) and 'embedding' in embedding_data:
                known_faces[user_id] = embedding_data['embedding']
            else:
                logger.warning(f"Unexpected embedding format for user {user_id}")
                continue
        
        logger.info(f"Prepared {len(known_faces)} faces for comparison")
        
        # Batch recognition
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "query_embedding": query_embedding,
                "known_faces": known_faces,
                "threshold": 0.4
            }
            
            logger.info(f"Sending batch recognize request with {len(known_faces)} known faces")
            
            response = await client.post(
                f"{ml_service_url}/batch-recognize",
                json=payload
            )
            
            if response.status_code != 200:
                logger.error(f"Batch recognition error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "recognized": False,
                    "message": "Face recognition failed"
                }
            
            result = response.json()
            logger.info(f"Recognition result: {result}")
            
            if result.get("recognized"):
                # Get user details
                user_model = User(db)
                user = await user_model.get_user_by_id(result["user_id"])
                
                if user:
                    logger.info(f"Face recognized: {user['email']} (similarity: {result.get('similarity')})")
                    return {
                        "success": True,
                        "recognized": True,
                        "user_id": result["user_id"],
                        "username": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                        "email": user.get("email"),
                        "confidence": result.get("similarity", 0.0),
                        "message": f"✅ Face recognized as {user.get('email')}"
                    }
            
            logger.info(f"Face not recognized (best similarity: {result.get('similarity')})")
            return {
                "success": True,
                "recognized": False,
                "message": f"Face not recognized. Best match similarity: {result.get('similarity', 0.0):.3f} (threshold: 0.4)",
                "best_similarity": result.get("similarity", 0.0)
            }
    
    except Exception as e:
        logger.error(f"Test face recognition failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face recognition test failed: {str(e)}"
        )






# ---------------------------------------------------------------------------
# ✅ Recognize Face from Video Frame (with station_id)
# ---------------------------------------------------------------------------
@router.post("/recognize-frame", response_model=Dict)
async def recognize_from_video_frame(
    station_id: str = Form(...),
    frame: UploadFile = File(...),
    db = Depends(get_database)
):
    """Recognize faces in a single video frame using embeddings-only DB"""
    
    if not frame.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"image": (frame.filename, await frame.read(), frame.content_type)}
            response = await client.post(f"{ML_SERVICE_URL}/extract-embedding", files=files)
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="ML service failed to process frame")
            
            result = response.json()
            if not result.get("success"):
                return {
                    "success": True,
                    "faces_detected": 0,
                    "recognition_results": [],
                    "station_id": station_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            face_data_model = FaceData(db)
            known_embeddings = await face_data_model.get_all_active_embeddings()
            
            if not known_embeddings:
                return {
                    "success": True,
                    "faces_detected": 1,
                    "recognition_results": [{
                        "recognized": False,
                        "message": "No registered users in database"
                    }],
                    "station_id": station_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # ✅ FIX: Flatten query embedding if it's 2D
            query_embedding = result.get("embedding")
            if isinstance(query_embedding, list) and len(query_embedding) == 1:
                query_embedding = query_embedding[0]  # Flatten from [512] to 512
            
            query_emb = np.array(query_embedding)
            best_match = None
            best_similarity = 0.0
            
            # Compare with stored embeddings
            for user_id, stored_embedding in known_embeddings.items():
                # ✅ Ensure stored embedding is also 1D
                stored_emb = np.array(stored_embedding)
                if stored_emb.ndim > 1:
                    stored_emb = stored_emb.flatten()
                
                # Cosine similarity
                similarity = float(np.dot(query_emb, stored_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(stored_emb)))
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = user_id
            
            recognition_result = {
                "recognized": best_similarity > 0.4,
                "user_id": best_match if best_similarity > 0.4 else None,
                "similarity": best_similarity
            }
            
            if best_match and best_similarity > 0.4:
                await face_data_model.update_recognition_stats(
                    user_id=best_match,
                    confidence=best_similarity,
                    location=station_id
                )
            
            return {
                "success": True,
                "faces_detected": 1,
                "recognition_results": [recognition_result],
                "station_id": station_id,
                "timestamp": datetime.utcnow().isoformat(),
                "database_size": len(known_embeddings)
            }
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML service unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Recognize frame failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



# ---------------------------------------------------------------------------
# ✅ Get User Embedding (ADMIN ONLY)
# ---------------------------------------------------------------------------
@router.get("/user/{user_id}/embedding")
async def get_user_embedding(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),  # ✅ Admin only!
    db=Depends(get_database)
):
    """Get user's face embedding (admin only)"""
    try:
        face_data_model = FaceData(db)
        embedding = await face_data_model.get_embedding(user_id)
        
        if embedding is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No face embedding found for user"
            )
        
        return {
            "success": True,
            "user_id": user_id,
            "embedding": embedding,
            "dimensions": len(embedding)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve embedding"
        )


# ---------------------------------------------------------------------------
# ✅ Delete User Embedding (ADMIN ONLY)
# ---------------------------------------------------------------------------
@router.delete("/user/{user_id}/embedding")
async def delete_user_embedding(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),  # ✅ Admin only!
    db=Depends(get_database)
):
    """Delete user's face embedding (admin only)"""
    try:
        face_data_model = FaceData(db)
        deleted = await face_data_model.delete_embedding(user_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No face embedding found for user"
            )
        
        return {
            "success": True,
            "message": "Face embedding deleted successfully",
            "user_id": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete embedding failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete embedding"
        )


# ---------------------------------------------------------------------------
# ✅ Health Check for Face Recognition System
# ---------------------------------------------------------------------------
@router.get("/health")
async def face_recognition_health_check():
    """Check connectivity and health of external ML service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ML_SERVICE_URL}/health")
            if response.status_code == 200:
                health_status = response.json()
                return {
                    "success": True,
                    "service": "face_recognition",
                    "status": health_status,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise HTTPException(status_code=500, detail="ML service returned error")
    except httpx.RequestError as e:
        return {
            "success": False,
            "service": "face_recognition",
            "status": "unreachable",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


