from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskStatus
from app.auth.auth_handler import get_current_user
from app.db.mongodb import get_database
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter()

async def auto_update_task_status(task: dict, db):
    now = datetime.utcnow()
    if task["status"] == TaskStatus.scheduled and task["scheduled_date"] < now:
        task["status"] = TaskStatus.uploaded
        await db["tasks"].update_one(
            {"_id": task["_id"]},
            {"$set": {"status": TaskStatus.uploaded, "updated_at": now}}
        )
    return task

@router.post("", response_model=TaskResponse)
async def create_task(task_in: TaskCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    task_dict = task_in.dict()
    task_dict["user_id"] = str(current_user["_id"])
    task_dict["created_at"] = datetime.utcnow()
    task_dict["updated_at"] = datetime.utcnow()
    
    result = await db["tasks"].insert_one(task_dict)
    task_dict["_id"] = str(result.inserted_id)
    return task_dict

@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    workspace_id: Optional[str] = None,
    filter: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    db = get_database()
    query = {"user_id": str(current_user["_id"])}
    
    if workspace_id:
        query["workspace_id"] = workspace_id
        
    now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if filter == "today":
        query["scheduled_date"] = {"$gte": now, "$lt": now + timedelta(days=1)}
    elif filter == "tomorrow":
        query["scheduled_date"] = {"$gte": now + timedelta(days=1), "$lt": now + timedelta(days=2)}
    elif filter == "upcoming":
        # Show next 3 days starting from day after tomorrow
        query["scheduled_date"] = {"$gte": now + timedelta(days=2), "$lt": now + timedelta(days=5)}
    
    cursor = db["tasks"].find(query).sort("scheduled_date", 1)
    tasks = []
    async for doc in cursor:
        doc = await auto_update_task_status(doc, db)
        doc["_id"] = str(doc["_id"])
        # Optionally add client name if it's a global view
        if not workspace_id:
            ws = await db["workspaces"].find_one({"_id": ObjectId(doc["workspace_id"])})
            if ws:
                doc["client_name"] = ws["client_name"]
        tasks.append(doc)
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    task = await db["tasks"].find_one({"_id": ObjectId(task_id), "user_id": str(current_user["_id"])})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = await auto_update_task_status(task, db)
    task["_id"] = str(task["_id"])
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_in: TaskUpdate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    update_data = {k: v for k, v in task_in.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    result = await db["tasks"].find_one_and_update(
        {"_id": ObjectId(task_id), "user_id": str(current_user["_id"])},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    result["_id"] = str(result["_id"])
    return result

@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    result = await db["tasks"].delete_one({"_id": ObjectId(task_id), "user_id": str(current_user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted"}
