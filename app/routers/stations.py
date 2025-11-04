from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, validator
from typing import List, Optional

from app.core.database import get_database
from app.core.security import get_current_user, get_current_admin_user
from app.models.station import Station
from app.models.fare import Fare

router = APIRouter()

# ✅ Schemas
class StationCreate(BaseModel):
    """Simplified station creation schema"""
    station_code: str
    station_name: str
    city: str
    
    @validator('station_code')
    def validate_station_code(cls, v):
        if len(v) < 3 or len(v) > 10:
            raise ValueError("Station code must be 3-10 characters")
        return v.upper()


class StationUpdate(BaseModel):
    """Simplified station update schema - all fields optional"""
    station_name: Optional[str] = None
    city: Optional[str] = None


class FareCreate(BaseModel):
    """Simplified fare creation schema"""
    from_station_code: str
    to_station_code: str
    distance_km: int
    base_fare: float
    
    @validator('base_fare')
    def validate_fare(cls, v):
        if v <= 0:
            raise ValueError("Fare must be positive")
        return v
    
    @validator('distance_km')
    def validate_distance(cls, v):
        if v <= 0:
            raise ValueError("Distance must be positive")
        return v


# ✅ PUT SPECIFIC ROUTES FIRST

@router.get("/get-fares")
async def get_all_fares(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get all fares - accessible by all authenticated users"""
    try:
        fare_model = Fare(db)
        fares = await fare_model.get_all_fares(skip, limit)
        
        return {
            "success": True,
            "count": len(fares),
            "fares": fares
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retrieve fares: {str(e)}"
        )


@router.get("/fares/calculate")
async def calculate_fare(
    from_station: str,
    to_station: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """Calculate fare between two stations - Simplified"""
    try:
        fare_model = Fare(db)
        fare = await fare_model.calculate_fare(from_station, to_station)
        
        return {
            "success": True,
            "fare": fare
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fare calculation failed: {str(e)}")


@router.post("/fares", status_code=status.HTTP_201_CREATED)
async def create_fare(
    fare_data: FareCreate,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Create or update fare between stations (admin only) - Simplified"""
    try:
        station_model = Station(db)
        
        # Get station IDs from station codes
        from_station = await station_model.get_station_by_code(fare_data.from_station_code)
        to_station = await station_model.get_station_by_code(fare_data.to_station_code)
        
        if not from_station:
            raise HTTPException(status_code=404, detail=f"From station {fare_data.from_station_code} not found")
        if not to_station:
            raise HTTPException(status_code=404, detail=f"To station {fare_data.to_station_code} not found")
        
        fare_model = Fare(db)
        fare_dict = {
            "from_station_id": str(from_station["_id"]),
            "to_station_id": str(to_station["_id"]),
            "from_station_code": fare_data.from_station_code.upper(),
            "to_station_code": fare_data.to_station_code.upper(),
            "distance_km": fare_data.distance_km,
            "base_fare": fare_data.base_fare
        }
        
        fare = await fare_model.create_fare(fare_dict)
        return {
            "success": True,
            "message": "Fare created/updated successfully",
            "fare": fare
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fare operation failed: {str(e)}")


# ✅ LIST ENDPOINT
@router.get("/")
async def list_stations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None),
    db = Depends(get_database)
):
    """List all stations with optional search"""
    try:
        station_model = Station(db)
        
        if search:
            stations = await station_model.search_stations(search)
        else:
            stations = await station_model.get_all_stations(skip, limit)
        
        total_count = await db.stations.count_documents({"is_active": True})
        
        return {
            "success": True,
            "stations": stations,
            "total": total_count,
            "page": skip // limit + 1 if limit > 0 else 1,
            "search_query": search
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list stations: {str(e)}")


# ✅ CREATE ENDPOINT
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_station(
    station_data: StationCreate,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Create new station (admin only) - Simplified"""
    try:
        station_model = Station(db)
        
        # ✅ Only use the 3 fields from simplified schema
        station_dict = {
            "station_code": station_data.station_code,
            "station_name": station_data.station_name,
            "city": station_data.city
        }
        
        station = await station_model.create_station(station_dict)
        return {
            "success": True,
            "message": "Station created successfully",
            "station": station
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Station creation failed: {str(e)}")


# ✅ UPDATE ENDPOINT
@router.put("/{station_id}")
async def update_station(
    station_id: str,
    update_data: StationUpdate,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Update station details (admin only) - Simplified"""
    try:
        station_model = Station(db)
        
        # ✅ Only extract fields that exist in StationUpdate schema
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        updated_station = await station_model.update_station(station_id, update_dict)
        
        if updated_station is None:
            raise HTTPException(status_code=404, detail="Station not found")
        
        return {
            "success": True,
            "message": "Station updated successfully",
            "station": updated_station
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Station update failed: {str(e)}")


# ✅ DELETE ENDPOINT
@router.delete("/{station_id}")
async def delete_station(
    station_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db = Depends(get_database)
):
    """Delete station (admin only)"""
    try:
        station_model = Station(db)
        deleted = await station_model.delete_station(station_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Station not found")
        
        return {
            "success": True,
            "message": "Station deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Station deletion failed: {str(e)}")


# ✅ PUT GENERIC ROUTES LAST

@router.get("/{station_id}")
async def get_station(
    station_id: str,
    db = Depends(get_database)
):
    """Get station details by ID"""
    try:
        station_model = Station(db)
        station = await station_model.get_station_by_id(station_id)
        
        if station is None:
            raise HTTPException(status_code=404, detail="Station not found")
        
        return {
            "success": True,
            "station": station
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get station: {str(e)}")



