from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse
from app.auth.auth_handler import get_current_user
from app.db.mongodb import get_database
from bson import ObjectId
from datetime import datetime
from typing import List

router = APIRouter()

@router.post("", response_model=WorkspaceResponse)
async def create_workspace(workspace_in: WorkspaceCreate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    workspace_dict = workspace_in.dict()
    workspace_dict["studio_id"] = current_user.get("studio_id")
    workspace_dict["created_by"] = str(current_user["_id"])
    workspace_dict["created_at"] = datetime.utcnow()
    
    result = await db["workspaces"].insert_one(workspace_dict)
    workspace_dict["_id"] = str(result.inserted_id)
    workspace_dict["user_id"] = workspace_dict["created_by"]
    if "studio_id" in workspace_dict and workspace_dict["studio_id"]:
        workspace_dict["studio_id"] = str(workspace_dict["studio_id"])
    return workspace_dict

@router.get("", response_model=List[WorkspaceResponse])
async def get_workspaces(current_user: dict = Depends(get_current_user)):
    db = get_database()
    studio_id = current_user.get("studio_id")
    cursor = db["workspaces"].find({"studio_id": studio_id})
    workspaces = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["user_id"] = doc.get("created_by")
        if "studio_id" in doc and doc["studio_id"]:
            doc["studio_id"] = str(doc["studio_id"])
        workspaces.append(doc)
    return workspaces

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    studio_id = current_user.get("studio_id")
    workspace = await db["workspaces"].find_one({"_id": ObjectId(workspace_id), "studio_id": studio_id})
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace["_id"] = str(workspace["_id"])
    workspace["user_id"] = workspace.get("created_by")
    if "studio_id" in workspace and workspace["studio_id"]:
        workspace["studio_id"] = str(workspace["studio_id"])
    return workspace

@router.put("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(workspace_id: str, workspace_in: WorkspaceUpdate, current_user: dict = Depends(get_current_user)):
    db = get_database()
    studio_id = current_user.get("studio_id")
    update_data = {k: v for k, v in workspace_in.dict().items() if v is not None}
    
    result = await db["workspaces"].find_one_and_update(
        {"_id": ObjectId(workspace_id), "studio_id": studio_id},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Workspace not found")
    result["_id"] = str(result["_id"])
    result["user_id"] = result.get("created_by")
    if "studio_id" in result and result["studio_id"]:
        result["studio_id"] = str(result["studio_id"])
    return result

@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    studio_id = current_user.get("studio_id")
    # Also delete tasks in this workspace - ensure they belong to same studio (safety)
    await db["tasks"].delete_many({"workspace_id": workspace_id, "studio_id": studio_id})
    result = await db["workspaces"].delete_one({"_id": ObjectId(workspace_id), "studio_id": studio_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"message": "Workspace deleted"}
