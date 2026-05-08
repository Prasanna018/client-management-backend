from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str = Field(alias="_id")
    studio_id: Optional[str] = None
    role: str = "staff"
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class StudioBase(BaseModel):
    name: str
    logo_url: Optional[str] = None

class StudioCreate(StudioBase):
    pass

class StudioResponse(StudioBase):
    id: str = Field(alias="_id")
    created_at: datetime
    is_active: bool = True

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
