from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.auth_handler import get_current_user, get_password_hash
from app.db.mongodb import get_database
from app.schemas.user import UserResponse, StudioResponse
from bson import ObjectId
from typing import List
from datetime import datetime

router = APIRouter()

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only studio admins can perform this action"
        )
    return current_user

@router.get("/me", response_model=StudioResponse)
async def get_studio_info(current_user: dict = Depends(get_current_user)):
    db = get_database()
    studio_id = current_user.get("studio_id")
    if not studio_id:
        raise HTTPException(status_code=404, detail="Studio not found for this user")
    
    studio = await db["studios"].find_one({"_id": studio_id})
    if not studio:
        raise HTTPException(status_code=404, detail="Studio not found")
    
    studio["_id"] = str(studio["_id"])
    return studio

@router.get("/members", response_model=List[UserResponse])
async def get_studio_members(admin: dict = Depends(get_admin_user)):
    db = get_database()
    studio_id = admin.get("studio_id")
    members = await db["users"].find({"studio_id": studio_id}).to_list(100)
    for m in members:
        m["_id"] = str(m["_id"])
    return members

@router.post("/members", response_model=UserResponse)
async def add_studio_member(member_data: dict, admin: dict = Depends(get_admin_user)):
    db = get_database()
    studio_id = admin.get("studio_id")
    
    email = member_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    existing = await db["users"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    new_user = {
        "username": email.split("@")[0],
        "email": email,
        "password": get_password_hash(member_data.get("password", "Welcome@123")),
        "studio_id": studio_id,
        "role": member_data.get("role", "staff"),
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    result = await db["users"].insert_one(new_user)
    new_user["_id"] = str(result.inserted_id)
    return new_user

@router.patch("/members/{user_id}")
async def toggle_member_status(user_id: str, status_data: dict, admin: dict = Depends(get_admin_user)):
    db = get_database()
    studio_id = admin.get("studio_id")
    
    is_active = status_data.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="is_active field is required")
    
    # Ensure user belongs to the same studio
    user = await db["users"].find_one({"_id": ObjectId(user_id), "studio_id": studio_id})
    if not user:
        raise HTTPException(status_code=404, detail="Member not found in your studio")
    
    # Prevent deactivating yourself
    if str(user["_id"]) == str(admin["_id"]):
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
        
    await db["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"is_active": is_active}}
    )
    return {"message": "Member status updated"}

@router.put("/settings")
async def update_studio_settings(settings: dict, admin: dict = Depends(get_admin_user)):
    db = get_database()
    studio_id = admin.get("studio_id")
    
    update_data = {}
    if "name" in settings:
        update_data["name"] = settings["name"]
    if "logo_url" in settings:
        update_data["logo_url"] = settings["logo_url"]
        
    if not update_data:
        raise HTTPException(status_code=400, detail="No settings provided to update")
        
    await db["studios"].update_one(
        {"_id": studio_id},
        {"$set": update_data}
    )
    return {"message": "Studio settings updated"}
