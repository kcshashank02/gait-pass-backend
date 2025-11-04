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





















# from fastapi import APIRouter, Depends, HTTPException, status
# from datetime import datetime
# import logging
# from bson import ObjectId

# from app.core.database import get_database
# from app.models.journey import Journey
# from app.models.wallet import Wallet
# from app.models.station import Station
# from app.models.fare import Fare

# router = APIRouter()
# logger = logging.getLogger(__name__)

# @router.post("/entry/{station_code}")
# async def automated_journey_entry(
#     station_code: str,  # ✅ Changed from station_id to station_code
#     recognized_user_id: str,  # This comes from face recognition
#     db=Depends(get_database)
# ):
#     """ENTRY: User face recognized at station entry gate"""
#     try:
#         # ✅ Convert station_code to station_id
#         station_model = Station(db)
#         entry_station = await station_model.get_station_by_code(station_code)
#         if entry_station is None:
#             return {
#                 "success": False,
#                 "action": "deny_entry",
#                 "message": f"Invalid station code: {station_code}",
#                 "gate_open": False
#             }
        
#         station_id = str(entry_station["_id"])
#         station_name = entry_station["station_name"]
        
#         # Check wallet balance
#         wallet_model = Wallet(db)
#         balance = await wallet_model.get_balance(recognized_user_id)
#         if balance < 20.0:
#             return {
#                 "success": False,
#                 "action": "deny_entry",
#                 "message": f"Insufficient balance {balance}. Minimum ₹20 required.",
#                 "gate_open": False,
#                 "current_balance": balance
#             }
        
#         # Start journey
#         journey_model = Journey(db)
#         journey = await journey_model.start_journey(
#             user_id=recognized_user_id,
#             entry_station_id=station_id,
#             entry_station_code=station_code
#         )
        
#         logger.info(f"User {recognized_user_id} entered at {station_name}")
#         return {
#             "success": True,
#             "action": "allow_entry",
#             "message": f"Welcome! Journey started at {station_name}",
#             "gate_open": True,
#             "journey_id": journey["journey_id"],
#             "entry_time": journey["entry_time"].isoformat(),
#             "current_balance": balance
#         }
        
#     except ValueError as e:
#         return {
#             "success": False,
#             "action": "deny_entry",
#             "message": str(e),
#             "gate_open": False
#         }
#     except Exception as e:
#         logger.error(f"Entry failed: {e}")
#         return {
#             "success": False,
#             "action": "deny_entry",
#             "message": "System error. Please try again.",
#             "gate_open": False
#         }


# @router.post("/exit/{station_code}")
# async def automated_journey_exit(
#     station_code: str,  # ✅ Changed from station_id to station_code
#     recognized_user_id: str,  # This comes from face recognition
#     db=Depends(get_database)
# ):
#     """EXIT: User face recognized at station exit gate"""
#     try:
#         # ✅ Convert station_code to station_id
#         journey_model = Journey(db)
#         ongoing_journey = await journey_model.get_ongoing_journey(recognized_user_id)
#         if ongoing_journey is None:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": "No ongoing journey found. Please tap in first.",
#                 "gate_open": False
#             }
        
#         station_model = Station(db)
#         exit_station = await station_model.get_station_by_code(station_code)
#         if exit_station is None:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": f"Invalid exit station code: {station_code}",
#                 "gate_open": False
#             }
        
#         station_id = str(exit_station["_id"])
#         station_name = exit_station["station_name"]
        
#         # Calculate fare
#         fare_model = Fare(db)
#         from_station_code = ongoing_journey["entry_station_code"]
#         current_hour = datetime.utcnow().hour
#         is_peak_hour = current_hour in [7, 8, 9, 17, 18, 19]  # Peak hours: 7-9 AM, 5-7 PM
        
#         fare_calculation = await fare_model.calculate_fare(
#             from_station_code=from_station_code,
#             to_station_code=station_code
#         )
        
#         if isinstance(fare_calculation, dict) and "error" in fare_calculation:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": f"Fare calculation error: {fare_calculation['error']}",
#                 "gate_open": False
#             }
        
#         total_fare = fare_calculation["total_fare"]
        
#         # Check wallet balance
#         wallet_model = Wallet(db)
#         balance = await wallet_model.get_balance(recognized_user_id)
#         if balance < total_fare:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": f"Insufficient balance {balance}. Fare ₹{total_fare}",
#                 "gate_open": False,
#                 "required_amount": total_fare,
#                 "current_balance": balance
#             }
        
#         # Deduct fare from wallet
#         wallet_transaction = {
#             "type": "debit",
#             "amount": total_fare,
#             "description": f"Journey fare {from_station_code} → {station_code}",
#             "reference": ongoing_journey["journey_id"]
#         }
#         transaction_success = await wallet_model.add_transaction(recognized_user_id, wallet_transaction)
        
#         if not transaction_success:
#             return {
#                 "success": False,
#                 "action": "deny_exit",
#                 "message": "Payment processing failed. Please try again.",
#                 "gate_open": False
#             }
        
#         # Complete journey
#         completed_journey = await journey_model.complete_journey(
#             user_id=recognized_user_id,
#             exit_station_id=station_id,
#             exit_station_code=station_code,
#             fare_calculation=fare_calculation
#         )
        
#         new_balance = balance - total_fare
#         logger.info(f"User {recognized_user_id} completed journey. ₹{total_fare} deducted")
        
#         return {
#             "success": True,
#             "action": "allow_exit",
#             "message": f"Journey completed! ₹{total_fare} deducted",
#             "gate_open": True,
#             "journey_details": {
#                 "journey_id": completed_journey["journey_id"],
#                 "from_station": from_station_code,
#                 "to_station": station_code,
#                 "entry_time": completed_journey["entry_time"].isoformat(),
#                 "exit_time": completed_journey["exit_time"].isoformat(),
#                 "duration_minutes": completed_journey["journey_duration_minutes"],
#                 "fare_paid": total_fare,
#                 "is_peak_hour": is_peak_hour
#             },
#             "wallet_details": {
#                 "previous_balance": balance,
#                 "fare_deducted": total_fare,
#                 "new_balance": new_balance
#             }
#         }
        
#     except Exception as e:
#         logger.error(f"Exit failed: {e}")
#         return {
#             "success": False,
#             "action": "deny_exit",
#             "message": "System error during exit. Please try again.",
#             "gate_open": False
#         }


# @router.get("/current-journey/{user_id}")
# async def get_current_journey(
#     user_id: str,
#     db=Depends(get_database)
# ):
#     """Get user's current ongoing journey"""
#     try:
#         journey_model = Journey(db)
#         ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
#         if ongoing_journey is None:
#             return {
#                 "success": True,
#                 "has_ongoing_journey": False,
#                 "message": "No ongoing journey found"
#             }
        
#         return {
#             "success": True,
#             "has_ongoing_journey": True,
#             "journey": ongoing_journey
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get journey: {str(e)}")


# @router.get("/history/{user_id}")
# async def get_journey_history(
#     user_id: str,
#     skip: int = 0,
#     limit: int = 50,
#     db=Depends(get_database)
# ):
#     """Get user's journey history"""
#     try:
#         journey_model = Journey(db)
#         history = await journey_model.get_user_journey_history(user_id, skip, limit)
        
#         return {
#             "success": True,
#             "journey_history": history,
#             "total_journeys": len(history)
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


# @router.post("/emergency-exit/{user_id}")
# async def emergency_exit(
#     user_id: str,
#     admin_user_id: str,  # Admin authorization required
#     db=Depends(get_database)
# ):
#     """Emergency exit for stuck users (admin only)"""
#     try:
#         journey_model = Journey(db)
#         ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
#         if ongoing_journey is None:
#             return {
#                 "success": False,
#                 "message": "No ongoing journey to cancel"
#             }
        
#         # Cancel ongoing journey without fare deduction
#         await journey_model.collection.update_one(
#             {"_id": ObjectId(ongoing_journey["_id"])},
#             {
#                 "$set": {
#                     "status": "emergency_cancelled",
#                     "cancelled_by_admin": admin_user_id,
#                     "cancelled_at": datetime.utcnow(),
#                     "updated_at": datetime.utcnow()
#                 }
#             }
#         )
        
#         return {
#             "success": True,
#             "message": "Emergency exit completed. Journey cancelled.",
#             "cancelled_journey_id": ongoing_journey["journey_id"]
#         }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Emergency exit failed: {str(e)}")















# # from fastapi import APIRouter, Depends, HTTPException, status
# # from fastapi.security import HTTPBearer
# # from datetime import datetime
# # import logging
# # from bson import ObjectId
# # from app.core.database import get_database
# # from app.models.journey import Journey
# # from app.models.wallet import Wallet
# # from app.models.station import Station
# # from app.models.fare import Fare
# # from app.services.ml_service import MLService

# # router = APIRouter()
# # logger = logging.getLogger(__name__)

# # async def get_ml_service() -> MLService:
# #     from app.main import ml_service
# #     return ml_service

# # @router.post("/entry/{station_id}")
# # async def automated_journey_entry(
# #     station_id: str,
# #     recognized_user_id: str,  # This comes from face recognition
# #     db = Depends(get_database)
# # ):
# #     """
# #     🚇 ENTRY: User face recognized at station entry gate
# #     Automatically starts journey and opens gate
# #     """
# #     try:
# #         # Verify station exists
# #         station_model = Station(db)
# #         entry_station = await station_model.get_station_by_id(station_id)
        
# #         if entry_station is None:
# #             return {
# #                 "success": False,
# #                 "action": "deny_entry",
# #                 "message": "Invalid station",
# #                 "gate_open": False
# #             }
        
# #         # Check wallet balance (minimum ₹20 required to enter)
# #         wallet_model = Wallet(db)
# #         balance = await wallet_model.get_balance(recognized_user_id)
        
# #         if balance < 20.0:
# #             return {
# #                 "success": False,
# #                 "action": "deny_entry", 
# #                 "message": f"Insufficient balance: ₹{balance}. Minimum ₹20 required.",
# #                 "gate_open": False,
# #                 "current_balance": balance
# #             }
        
# #         # Start journey
# #         journey_model = Journey(db)
# #         journey = await journey_model.start_journey(
# #             user_id=recognized_user_id,
# #             entry_station_id=station_id,
# #             entry_station_code=entry_station["station_code"]
# #         )
        
# #         logger.info(f"✅ User {recognized_user_id} entered at {entry_station['station_name']}")
        
# #         return {
# #             "success": True,
# #             "action": "allow_entry",
# #             "message": f"Welcome! Journey started at {entry_station['station_name']}",
# #             "gate_open": True,
# #             "journey_id": journey["journey_id"],
# #             "entry_time": journey["entry_time"].isoformat(),
# #             "current_balance": balance
# #         }
        
# #     except ValueError as e:
# #         return {
# #             "success": False,
# #             "action": "deny_entry",
# #             "message": str(e),
# #             "gate_open": False
# #         }
# #     except Exception as e:
# #         logger.error(f"❌ Entry failed: {e}")
# #         return {
# #             "success": False,
# #             "action": "deny_entry", 
# #             "message": "System error. Please try again.",
# #             "gate_open": False
# #         }

# # @router.post("/exit/{station_id}")
# # async def automated_journey_exit(
# #     station_id: str,
# #     recognized_user_id: str,  # This comes from face recognition
# #     db = Depends(get_database)
# # ):
# #     """
# #     🚇 EXIT: User face recognized at station exit gate  
# #     Automatically calculates fare, deducts from wallet, completes journey
# #     """
# #     try:
# #         # Get ongoing journey
# #         journey_model = Journey(db)
# #         ongoing_journey = await journey_model.get_ongoing_journey(recognized_user_id)
        
# #         if ongoing_journey is None:
# #             return {
# #                 "success": False,
# #                 "action": "deny_exit",
# #                 "message": "No ongoing journey found. Please tap in first.",
# #                 "gate_open": False
# #             }
        
# #         # Verify exit station
# #         station_model = Station(db)
# #         exit_station = await station_model.get_station_by_id(station_id)
        
# #         if exit_station is None:
# #             return {
# #                 "success": False,
# #                 "action": "deny_exit",
# #                 "message": "Invalid exit station",
# #                 "gate_open": False
# #             }
        
# #         # Calculate fare
# #         fare_model = Fare(db)
# #         current_hour = datetime.utcnow().hour
# #         is_peak_hour = current_hour in [7, 8, 9, 17, 18, 19]  # Peak hours: 7-9 AM, 5-7 PM
        
# #         fare_calculation = await fare_model.calculate_fare(
# #             from_station_code=ongoing_journey["entry_station_code"],
# #             to_station_code=exit_station["station_code"],
# #             is_express=False,
# #             is_peak_hour=is_peak_hour
# #         )
        
# #         if "error" in fare_calculation:
# #             return {
# #                 "success": False,
# #                 "action": "deny_exit",
# #                 "message": f"Fare calculation error: {fare_calculation['error']}",
# #                 "gate_open": False
# #             }
        
# #         total_fare = fare_calculation["total_fare"]
        
# #         # Check wallet balance
# #         wallet_model = Wallet(db)
# #         balance = await wallet_model.get_balance(recognized_user_id)
        
# #         if balance < total_fare:
# #             return {
# #                 "success": False,
# #                 "action": "deny_exit",
# #                 "message": f"Insufficient balance: ₹{balance}. Fare: ₹{total_fare}",
# #                 "gate_open": False,
# #                 "required_amount": total_fare,
# #                 "current_balance": balance,
# #                 "shortfall": total_fare - balance
# #             }
        
# #         # Deduct fare from wallet
# #         wallet_transaction = {
# #             "type": "debit",
# #             "amount": total_fare,
# #             "description": f"Journey fare: {ongoing_journey['entry_station_code']} → {exit_station['station_code']}",
# #             "reference": ongoing_journey["journey_id"]
# #         }
        
# #         transaction_success = await wallet_model.add_transaction(recognized_user_id, wallet_transaction)
        
# #         if not transaction_success:
# #             return {
# #                 "success": False,
# #                 "action": "deny_exit",
# #                 "message": "Payment processing failed. Please try again.",
# #                 "gate_open": False
# #             }
        
# #         # Complete journey
# #         completed_journey = await journey_model.complete_journey(
# #             user_id=recognized_user_id,
# #             exit_station_id=station_id,
# #             exit_station_code=exit_station["station_code"],
# #             fare_calculation=fare_calculation
# #         )
        
# #         new_balance = balance - total_fare
        
# #         logger.info(f"✅ User {recognized_user_id} completed journey: ₹{total_fare} deducted")
        
# #         return {
# #             "success": True,
# #             "action": "allow_exit",
# #             "message": f"Journey completed! Fare: ₹{total_fare} deducted",
# #             "gate_open": True,
# #             "journey_details": {
# #                 "journey_id": completed_journey["journey_id"],
# #                 "from_station": ongoing_journey["entry_station_code"],
# #                 "to_station": exit_station["station_code"],
# #                 "entry_time": ongoing_journey["entry_time"].isoformat(),
# #                 "exit_time": completed_journey["exit_time"].isoformat(),
# #                 "duration_minutes": completed_journey["journey_duration_minutes"],
# #                 "fare_paid": total_fare,
# #                 "is_peak_hour": is_peak_hour
# #             },
# #             "wallet_details": {
# #                 "previous_balance": balance,
# #                 "fare_deducted": total_fare,
# #                 "new_balance": new_balance
# #             }
# #         }
        
# #     except Exception as e:
# #         logger.error(f"❌ Exit failed: {e}")
# #         return {
# #             "success": False,
# #             "action": "deny_exit",
# #             "message": "System error during exit. Please try again.",
# #             "gate_open": False
# #         }

# # @router.get("/current-journey/{user_id}")
# # async def get_current_journey(
# #     user_id: str,
# #     db = Depends(get_database)
# # ):
# #     """Get user's current ongoing journey"""
# #     try:
# #         journey_model = Journey(db)
# #         ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
# #         if ongoing_journey is None:
# #             return {
# #                 "success": True,
# #                 "has_ongoing_journey": False,
# #                 "message": "No ongoing journey found"
# #             }
        
# #         return {
# #             "success": True,
# #             "has_ongoing_journey": True,
# #             "journey": ongoing_journey
# #         }
        
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Failed to get journey: {str(e)}")

# # @router.get("/history/{user_id}")
# # async def get_journey_history(
# #     user_id: str,
# #     skip: int = 0,
# #     limit: int = 50,
# #     db = Depends(get_database)
# # ):
# #     """Get user's journey history"""
# #     try:
# #         journey_model = Journey(db)
# #         history = await journey_model.get_user_journey_history(user_id, skip, limit)
        
# #         return {
# #             "success": True,
# #             "journey_history": history,
# #             "total_journeys": len(history)
# #         }
        
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

# # @router.post("/emergency-exit/{user_id}")
# # async def emergency_exit(
# #     user_id: str,
# #     admin_user_id: str,  # Admin authorization required
# #     db = Depends(get_database)
# # ):
# #     """Emergency exit for stuck users (admin only)"""
# #     try:
# #         journey_model = Journey(db)
# #         ongoing_journey = await journey_model.get_ongoing_journey(user_id)
        
# #         if ongoing_journey is None:
# #             return {"success": False, "message": "No ongoing journey to cancel"}
        
# #         # Cancel ongoing journey without fare deduction
# #         await journey_model.collection.update_one(
# #             {"_id": ObjectId(ongoing_journey["_id"])},
# #             {
# #                 "$set": {
# #                     "status": "emergency_cancelled",
# #                     "cancelled_by_admin": admin_user_id,
# #                     "cancelled_at": datetime.utcnow(),
# #                     "updated_at": datetime.utcnow()
# #                 }
# #             }
# #         )
        
# #         return {
# #             "success": True,
# #             "message": "Emergency exit completed. Journey cancelled.",
# #             "cancelled_journey_id": ongoing_journey["journey_id"]
# #         }
        
# #     except Exception as e:
# #         raise HTTPException(status_code=500, detail=f"Emergency exit failed: {str(e)}")
