from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import logging
from bson import ObjectId

from app.core.security import get_current_user, get_current_admin_user
from app.core.database import get_database
from app.models.journey import Journey
from app.models.wallet import Wallet
from app.models.station import Station
from app.models.fare import Fare

router = APIRouter()
logger = logging.getLogger(__name__)


# ✅ ENTRY - ADMIN ONLY
@router.post("/entry/{station_code}")
async def automated_journey_entry(
    station_code: str,
    recognized_user_id: str,
    admin_user: dict = Depends(get_current_admin_user),  # ✅ ADMIN REQUIRED
    db=Depends(get_database)
):
    """Entry - Only station operator/admin can authorize gate opening"""
    try:
        station_model = Station(db)
        entry_station = await station_model.get_station_by_code(station_code)
        if entry_station is None:
            return {"success": False, "action": "deny_entry", "message": "Invalid station", "gate_open": False}

        wallet_model = Wallet(db)
        balance = await wallet_model.get_balance(recognized_user_id)
        if balance < 20:
            return {"success": False, "action": "deny_entry", "message": "Insufficient balance", "gate_open": False}

        journey_model = Journey(db)
        journey = await journey_model.start_journey(
            user_id=recognized_user_id,
            entry_station_id=str(entry_station["_id"]),
            entry_station_code=station_code
        )

        return {
            "success": True,
            "action": "allow_entry",
            "message": f"Journey started at {entry_station['station_name']}",
            "gate_open": True,
            "journey_id": journey["journey_id"],
            "entry_time": journey["entry_time"].isoformat(),
            "current_balance": balance
        }

    except Exception as e:
        logger.error(e)
        return {"success": False, "action": "deny_entry", "message": "System error", "gate_open": False}


# ✅ EXIT - ADMIN ONLY
@router.post("/exit/{station_code}")
async def automated_journey_exit(
    station_code: str,
    recognized_user_id: str,
    admin_user: dict = Depends(get_current_admin_user),  # ✅ ADMIN REQUIRED
    db=Depends(get_database)
):
    """Exit - Only station operator/admin can authorize gate opening"""
    try:
        journey_model = Journey(db)
        ongoing_journey = await journey_model.get_ongoing_journey(recognized_user_id)
        if ongoing_journey is None:
            return {"success": False, "action": "deny_exit", "message": "No journey ongoing", "gate_open": False}

        station_model = Station(db)
        exit_station = await station_model.get_station_by_code(station_code)
        if exit_station is None:
            return {"success": False, "action": "deny_exit", "message": "Invalid station", "gate_open": False}

        fare_model = Fare(db)
        fare = await fare_model.calculate_fare(
            from_station_code=ongoing_journey["entry_station_code"],
            to_station_code=station_code
        )

        total_fare = fare["total_fare"]
        wallet_model = Wallet(db)
        balance = await wallet_model.get_balance(recognized_user_id)

        if balance < total_fare:
            return {"success": False, "action": "deny_exit", "message": "Low balance", "gate_open": False}

        await wallet_model.add_transaction(recognized_user_id, {
            "type": "debit",
            "amount": total_fare,
            "description": f"Fare {ongoing_journey['entry_station_code']} → {station_code}",
            "reference": ongoing_journey["journey_id"]
        })

        completed_journey = await journey_model.complete_journey(
            user_id=recognized_user_id,
            exit_station_id=str(exit_station["_id"]),
            exit_station_code=station_code,
            fare_calculation=fare
        )

        return {
            "success": True,
            "action": "allow_exit",
            "message": f"Journey completed. ₹{total_fare} deducted",
            "gate_open": True,
            "journey_details": completed_journey
        }

    except Exception as e:
        logger.error(e)
        return {"success": False, "action": "deny_exit", "message": "System error", "gate_open": False}


# ✅ CURRENT JOURNEY - USER OR ADMIN

@router.get("/current-journey/{user_id}")
async def get_current_journey(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get Current Journey
    - Users can see ONLY their own current journey
    - Admin can see ANY user's current journey
    """
    try:
        # ✅ Use '_id' field instead of 'user_id'
        current_user_id = str(current_user.get("_id"))
        requested_user_id = str(user_id)
        
        # ✅ Check permissions
        is_admin = current_user.get("role") == "admin"
        is_own_journey = current_user_id == requested_user_id
        
        if not is_admin and not is_own_journey:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own journey"
            )
        
        journey_model = Journey(db)
        ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
        if ongoing_journey is None:
            return {
                "success": False,
                "message": "No ongoing journey found",
                "journey": None
            }
        
        # Convert ObjectIds to strings
        ongoing_journey["_id"] = str(ongoing_journey["_id"])
        ongoing_journey["user_id"] = str(ongoing_journey["user_id"])
        
        return {
            "success": True,
            "message": "Current journey retrieved",
            "journey": ongoing_journey
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get current journey failed: {e}")
        return {
            "success": False,
            "message": str(e),
            "journey": None
        }


@router.get("/history/{user_id}")
async def get_journey_history(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get Journey History
    - Users can see ONLY their own journey history
    - Admin can see ANY user's journey history
    """
    try:
        # ✅ Use '_id' field instead of 'user_id'
        current_user_id = str(current_user.get("_id"))
        requested_user_id = str(user_id)
        
        # ✅ Check permissions
        is_admin = current_user.get("role") == "admin"
        is_own_history = current_user_id == requested_user_id
        
        if not is_admin and not is_own_history:
            raise HTTPException(
                status_code=403,
                detail="You can only view your own journey history"
            )
        
        journey_model = Journey(db)
        # ✅ Use correct method name: get_user_journey_history
        journeys = await journey_model.get_user_journey_history(user_id, skip, limit)
        
        # ✅ Count total journeys for the user
        total = len(journeys)  # or query count from db
        
        # Convert ObjectIds to strings
        for journey in journeys:
            journey["_id"] = str(journey["_id"])
            journey["user_id"] = str(journey["user_id"])
        
        return {
            "success": True,
            "message": "Journey history retrieved",
            "journeys": journeys,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get journey history failed: {e}")
        return {
            "success": False,
            "message": str(e),
            "journeys": []
        }




# ✅ EMERGENCY EXIT - ADMIN ONLY
@router.post("/emergency-exit/{user_id}")
async def emergency_exit_admin(
    user_id: str,
    admin_user: dict = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    journey_model = Journey(db)
    ongoing = await journey_model.get_ongoing_journey(user_id)

    if not ongoing:
        return {"success": False, "message": "No journey to cancel"}

    await journey_model.collection.update_one(
        {"_id": ObjectId(ongoing["_id"])},
        {"$set": {"status": "emergency_cancelled", "cancelled_at": datetime.utcnow()}}
    )
    return {"success": True, "message": "Journey cancelled"}







