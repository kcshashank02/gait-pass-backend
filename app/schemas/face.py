from pydantic import BaseModel, validator
from typing import List, Optional, Dict
from datetime import datetime

class FaceRegistrationRequest(BaseModel):
    user_id: str
    person_name: str

class FaceRegistrationResponse(BaseModel):
    success: bool
    message: str
    face_data_id: str
    images_processed: int
    registration_quality: str
    confidence: float

class RecognitionRequest(BaseModel):
    station_id: str

class RecognitionResult(BaseModel):
    bbox: List[int]
    confidence: float
    similarity: float
    recognized: bool
    user: Optional[Dict] = None

class RecognitionResponse(BaseModel):
    success: bool
    faces_detected: int
    recognition_results: List[RecognitionResult]
    station_id: str
    timestamp: str

class FaceDataResponse(BaseModel):
    id: str
    user_id: str
    person_name: str
    registration_quality: str
    confidence: float
    registered_images: int
    total_recognitions: int
    last_recognized: Optional[datetime]
    created_at: datetime
