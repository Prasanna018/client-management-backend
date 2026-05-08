from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from bson import ObjectId

class PostType(str, Enum):
    post = "post"
    reel = "reel"


class TaskStatus(str, Enum):
    pending = "pending"
    scheduled = "scheduled"
    uploaded = "uploaded"

class TaskBase(BaseModel):
    title: str
    scheduled_date: datetime
    post_type: PostType
    status: TaskStatus = TaskStatus.pending
    notes: Optional[str] = None

class TaskCreate(TaskBase):
    workspace_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    post_type: Optional[PostType] = None
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None

class TaskResponse(TaskBase):
    id: str = Field(alias="_id")
    workspace_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    client_name: Optional[str] = None # For global view

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
