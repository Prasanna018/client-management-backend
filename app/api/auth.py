from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import UserCreate, UserResponse, Token
from app.auth.auth_handler import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token, get_current_user
from app.db.mongodb import get_database
from datetime import datetime

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_in: UserCreate):
    db = get_database()
    # Check if user exists
    existing_user = await db["users"].find_one({"$or": [{"email": user_in.email}, {"username": user_in.username}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_dict = user_in.dict()
    user_dict["password"] = get_password_hash(user_dict["password"])
    user_dict["created_at"] = datetime.utcnow()
    
    result = await db["users"].insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    return user_dict

@router.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_database()
    user = await db["users"].find_one({"$or": [{"email": form_data.username}, {"username": form_data.username}]})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect email/username or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    refresh_token = create_refresh_token(data={"sub": str(user["_id"])})
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False, # Set to False so user can see/access them if they want, but True is better for security
        max_age=3600, # 1 hour
        samesite="lax",
        secure=False # Set to True in production with HTTPS
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=False,
        max_age=604800, # 7 days
        samesite="lax",
        secure=False
    )
    
    return {"message": "Login successful"}

@router.post("/refresh")
async def refresh_token_endpoint(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    new_access_token = create_access_token(data={"sub": user_id})
    new_refresh_token = create_refresh_token(data={"sub": user_id})
    
    response.set_cookie(key="access_token", value=new_access_token, httponly=False, max_age=3600, samesite="lax")
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=False, max_age=604800, samesite="lax")
    
    return {"message": "Token refreshed"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", samesite="lax")
    response.delete_cookie(key="refresh_token", samesite="lax")
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    current_user["_id"] = str(current_user["_id"])
    return current_user
