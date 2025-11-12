# from fastapi import APIRouter, Depends, HTTPException
# from datetime import datetime
# import logging
# from bson import ObjectId
# from app.core.security import get_current_user, get_current_admin_user
# from app.core.database import get_database
# from app.models.journey import Journey
# from app.models.wallet import Wallet
# from app.models.station import Station
# from app.models.fare import Fare

# router = APIRouter()
# logger = logging.getLogger(__name__)

# # Minimum base fare for same station exit
# SAME_STATION_BASE_FARE = 5.0
# SERVICE_CHARGE = 5.0


# @router.post("/entry/{station_code}")
# async def automated_journey_entry(
#     station_code: str,
#     recognized_user_id: str,
#     admin_user: dict = Depends(get_current_admin_user),
#     db=Depends(get_database)
# ):
#     """
#     ENTRY - Only station operator/admin can authorize gate opening
#     """
#     try:
#         # Get station details
#         station_model = Station(db)
#         entry_station = await station_model.get_station_by_code(station_code)
        
#         if entry_station is None:
#             return {
#                 "success": False,
#                 "action": "deny_entry",
#                 "message": "Invalid station",
#                 "gate_open": False
#             }
        
#         # Check wallet balance
#         wallet_model = Wallet(db)
#         balance = await wallet_model.get_balance(recognized_user_id)
        
#         if balance < 20:
#             return {
#                 "success": False,
#                 "action": "deny_entry",
#                 "message": f"Insufficient balance. Current balance: ₹{balance}. Minimum required: ₹20",
#                 "gate_open": False,
#                 "current_balance": balance
#             }
        
#         # Check for ongoing journey
#         journey_model = Journey(db)
#         ongoing = await journey_model.get_ongoing_journey(recognized_user_id)
        
#         if ongoing:
#             entry_station_name = ongoing.get('entry_station_code', 'Unknown')
#             return {
#                 "success": False,
#                 "action": "deny_entry",
#                 "message": f"You have an ongoing journey from {entry_station_name}. Please complete your exit first.",
#                 "gate_open": False,
#                 "ongoing_journey": {
#                     "journey_id": ongoing.get('journey_id'),
#                     "entry_station": entry_station_name,
#                     "entry_time": ongoing.get('entry_time')
#                 }
#             }
        
#         # Start journey
#         journey = await journey_model.start_journey(
#             user_id=recognized_user_id,
#             entry_station_id=str(entry_station["_id"]),
#             entry_station_code=station_code
#         )
        
#         return {
#             "success": True,
#             "action": "allow_entry",
#             "message": f"Journey started at {entry_station['station_name']}",
#             "gate_open": True,
#             "journey_id": journey["journey_id"],
#             "entry_time": journey["entry_time"].isoformat(),
#             "current_balance": balance
#         }
        
#     except Exception as e:
#         logger.error(e)
#         return {
#             "success": False,
#             "action": "deny_entry",
#             "message": "System error. Please try again.",
#             "gate_open": False
#         }


# @router.post("/exit/{station_code}")
# async def automated_journey_exit(
#     station_code: str,
#     recognized_user_id: str,
#     admin_user: dict = Depends(get_current_admin_user),
#     db=Depends(get_database)
# ):
#     """
#     EXIT - Only station operator/admin can authorize gate opening
#     Handles same station exit with minimum base fare
#     """
#     try:
#         # Check for ongoing journey
#         journey_model = Journey(db)
#         ongoing_journey = await journey_model.get_ongoing_journey(recognized_user_id)
        
#         if ongoing_journey is None:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": "No ongoing journey found. Please tap at entry gate first.",
#                 "gate_open": False
#             }
        
#         # Get exit station details
#         station_model = Station(db)
#         exit_station = await station_model.get_station_by_code(station_code)
        
#         if exit_station is None:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": "Invalid station",
#                 "gate_open": False
#             }
        
#         entry_station_code = ongoing_journey["entry_station_code"]
#         exit_station_code = station_code
        
#         # Check if same station exit
#         is_same_station = entry_station_code.upper() == exit_station_code.upper()
        
#         if is_same_station:
#             # Same station exit - apply minimum base fare
#             fare = {
#                 "from_station": entry_station_code,
#                 "to_station": exit_station_code,
#                 "distance_km": 0,
#                 "base_fare": SAME_STATION_BASE_FARE,
#                 "service_charge": SERVICE_CHARGE,
#                 "total_fare": SAME_STATION_BASE_FARE + SERVICE_CHARGE
#             }
#             logger.info(f"Same station exit detected: {entry_station_code}. Applying base fare: ₹{SAME_STATION_BASE_FARE}")
#         else:
#             # Different station exit - calculate normal fare
#             fare_model = Fare(db)
#             try:
#                 fare = await fare_model.calculate_fare(
#                     from_station_code=entry_station_code,
#                     to_station_code=exit_station_code
#                 )
#             except ValueError as ve:
#                 # No fare configured between stations
#                 logger.error(f"Fare calculation error: {ve}")
#                 return {
#                     "success": False,
#                     "action": "deny_exit",
#                     "message": f"No fare configured for route {entry_station_code} → {exit_station_code}",
#                     "gate_open": False
#                 }
        
#         total_fare = fare["total_fare"]
        
#         # Check wallet balance
#         wallet_model = Wallet(db)
#         balance = await wallet_model.get_balance(recognized_user_id)
        
#         if balance < total_fare:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": f"Insufficient balance. Required: ₹{total_fare}, Available: ₹{balance}",
#                 "gate_open": False,
#                 "fare_required": total_fare,
#                 "current_balance": balance
#             }
        
#         # Deduct fare from wallet
#         await wallet_model.add_transaction(
#             recognized_user_id,
#             type="debit",
#             amount=total_fare,
#             description=f"Fare: {entry_station_code} → {exit_station_code}" + 
#                        (" (Same Station)" if is_same_station else ""),
#             reference=ongoing_journey["journey_id"]
#         )
        
#         # Complete journey
#         completed_journey = await journey_model.complete_journey(
#             user_id=recognized_user_id,
#             exit_station_id=str(exit_station["_id"]),
#             exit_station_code=station_code,
#             fare_calculation=fare
#         )
        
#         exit_message = f"Journey completed. Fare: ₹{total_fare}"
#         if is_same_station:
#             exit_message += " (Same station - Base fare applied)"
        
#         return {
#             "success": True,
#             "action": "allow_exit",
#             "message": exit_message,
#             "gate_open": True,
#             "journey_details": completed_journey,
#             "current_balance": balance - total_fare
#         }
        
#     except Exception as e:
#         logger.error(f"Exit error: {e}")
#         return {
#             "success": False,
#             "action": "deny_exit",
#             "message": "System error. Please contact support.",
#             "gate_open": False
#         }


# @router.get("/current-journey/{user_id}")
# async def get_current_journey(
#     user_id: str,
#     current_user: dict = Depends(get_current_user),
#     db=Depends(get_database)
# ):
#     """Get Current Journey - Users can see ONLY their own current journey - Admin can see ANY user's current journey"""
#     try:
#         current_user_id = str(current_user.get("_id"))
#         requested_user_id = str(user_id)
        
#         is_admin = current_user.get("role") == "admin"
#         is_own_journey = current_user_id == requested_user_id
        
#         if not is_admin and not is_own_journey:
#             raise HTTPException(status_code=403, detail="You can only view your own journey")
        
#         journey_model = Journey(db)
#         ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
#         if ongoing_journey is None:
#             return {
#                 "success": False,
#                 "message": "No ongoing journey found",
#                 "journey": None
#             }
        
#         ongoing_journey["_id"] = str(ongoing_journey["_id"])
#         ongoing_journey["user_id"] = str(ongoing_journey["user_id"])
        
#         return {
#             "success": True,
#             "message": "Current journey retrieved",
#             "journey": ongoing_journey
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Get current journey failed: {e}")
#         return {
#             "success": False,
#             "message": str(e),
#             "journey": None
#         }


# @router.get("/history/{user_id}")
# async def get_journey_history(
#     user_id: str,
#     skip: int = 0,
#     limit: int = 50,
#     current_user: dict = Depends(get_current_user),
#     db=Depends(get_database)
# ):
#     """Get Journey History - Users can see ONLY their own journey history - Admin can see ANY user's journey history"""
#     try:
#         current_user_id = str(current_user.get("_id"))
#         requested_user_id = str(user_id)
        
#         is_admin = current_user.get("role") == "admin"
#         is_own_history = current_user_id == requested_user_id
        
#         if not is_admin and not is_own_history:
#             raise HTTPException(status_code=403, detail="You can only view your own journey history")
        
#         journey_model = Journey(db)
#         journeys = await journey_model.get_user_journey_history(user_id, skip, limit)
        
#         total = len(journeys)
        
#         for journey in journeys:
#             journey["_id"] = str(journey["_id"])
#             journey["user_id"] = str(journey["user_id"])
        
#         return {
#             "success": True,
#             "message": "Journey history retrieved",
#             "journeys": journeys,
#             "total": total,
#             "skip": skip,
#             "limit": limit
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Get journey history failed: {e}")
#         return {
#             "success": False,
#             "message": str(e),
#             "journeys": []
#         }


# @router.post("/emergency-exit/{user_id}")
# async def emergency_exit_admin(
#     user_id: str,
#     admin_user: dict = Depends(get_current_admin_user),
#     db=Depends(get_database)
# ):
#     """Emergency exit - Admin only"""
#     journey_model = Journey(db)
#     ongoing = await journey_model.get_ongoing_journey(user_id)
    
#     if not ongoing:
#         return {"success": False, "message": "No journey to cancel"}
    
#     await journey_model.collection.update_one(
#         {"_id": ObjectId(ongoing["_id"])},
#         {"$set": {"status": "emergency_cancelled", "cancelled_at": datetime.utcnow()}}
#     )
    
#     return {"success": True, "message": "Journey cancelled"}

















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


# @router.get("/history/{user_id}")
# async def get_journey_history(
#     user_id: str,
#     skip: int = 0,
#     limit: int = 50,
#     current_user: dict = Depends(get_current_user),
#     db=Depends(get_database)
# ):
#     """
#     Get Journey History
#     - Users can see ONLY their own journey history
#     - Admin can see ANY user's journey history
#     """
#     try:
#         # ✅ Use '_id' field instead of 'user_id'
#         current_user_id = str(current_user.get("_id"))
#         requested_user_id = str(user_id)
        
#         # ✅ Check permissions
#         is_admin = current_user.get("role") == "admin"
#         is_own_history = current_user_id == requested_user_id
        
#         if not is_admin and not is_own_history:
#             raise HTTPException(
#                 status_code=403,
#                 detail="You can only view your own journey history"
#             )
        
#         journey_model = Journey(db)
#         # ✅ Use correct method name: get_user_journey_history
#         journeys = await journey_model.get_user_journey_history(user_id, skip, limit)
        
#         # ✅ Count total journeys for the user
#         total = len(journeys)  # or query count from db
        
#         # Convert ObjectIds to strings
#         for journey in journeys:
#             journey["_id"] = str(journey["_id"])
#             journey["user_id"] = str(journey["user_id"])
        
#         return {
#             "success": True,
#             "message": "Journey history retrieved",
#             "journeys": journeys,
#             "total": total,
#             "skip": skip,
#             "limit": limit
#         }
        
#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"Get journey history failed: {e}")
#         return {
#             "success": False,
#             "message": str(e),
#             "journeys": []
#         }


@router.get("/history/{user_id}")
async def get_journey_history(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get Journey History with Station Names
    - Users can see ONLY their own journey history
    - Admin can see ANY user's journey history
    """
    try:
        current_user_id = str(current_user.get("_id"))
        requested_user_id = str(user_id)
        
        is_admin = current_user.get("role") == "admin"
        is_own_history = current_user_id == requested_user_id
        
        if not is_admin and not is_own_history:
            raise HTTPException(status_code=403, detail="You can only view your own journey history")
        
        # ✅ FIX: Use MongoDB aggregation to join station data
        from bson import ObjectId
        
        pipeline = [
            # Match user's completed journeys
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "status": "completed",
                    "is_active": True
                }
            },
            # Sort by exit time (most recent first)
            {"$sort": {"exit_time": -1}},
            # Pagination
            {"$skip": skip},
            {"$limit": limit},
            # Lookup entry station details
            {
                "$lookup": {
                    "from": "stations",
                    "localField": "entry_station_id",
                    "foreignField": "_id",
                    "as": "entry_station_details"
                }
            },
            # Lookup exit station details
            {
                "$lookup": {
                    "from": "stations",
                    "localField": "exit_station_id",
                    "foreignField": "_id",
                    "as": "exit_station_details"
                }
            },
            # Unwind station arrays
            {"$unwind": {"path": "$entry_station_details", "preserveNullAndEmptyArrays": True}},
            {"$unwind": {"path": "$exit_station_details", "preserveNullAndEmptyArrays": True}},
            # Project final fields
            {
                "$project": {
                    "_id": 1,
                    "journey_id": 1,
                    "user_id": 1,
                    "entry_station_code": 1,
                    "entry_station_name": "$entry_station_details.station_name",
                    "entry_time": 1,
                    "exit_station_code": 1,
                    "exit_station_name": "$exit_station_details.station_name",
                    "exit_time": 1,
                    "journey_duration_minutes": 1,
                    "fare_details": 1,
                    "status": 1,
                    "is_peak_hour": 1,
                    "created_at": 1
                }
            }
        ]
        
        # Execute aggregation
        journeys = []
        async for journey in db.journeys.aggregate(pipeline):
            journey["_id"] = str(journey["_id"])
            journey["user_id"] = str(journey["user_id"])
            journeys.append(journey)
        
        # Get total count
        total = await db.journeys.count_documents({
            "user_id": ObjectId(user_id),
            "status": "completed",
            "is_active": True
        })
        
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







