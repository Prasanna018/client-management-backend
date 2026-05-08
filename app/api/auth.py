from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.schemas.user import UserCreate, UserResponse, Token
from app.auth.auth_handler import get_password_hash, verify_password, create_access_token, create_refresh_token, decode_token, get_current_user
from app.db.mongodb import get_database
from datetime import datetime

router = APIRouter()



@router.post("/login")
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_database()
    user = await db["users"].find_one({"$or": [{"email": form_data.username}, {"username": form_data.username}]})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=400, detail="Incorrect email/username or password")
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    refresh_token = create_refresh_token(data={"sub": str(user["_id"])})
    
    # Set cookies for production (cross-site)
    # Note: samesite="none" REQUIRES secure=True (HTTPS)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=False, 
        max_age=3600, 
        samesite="none",
        secure=True,
        path="/"
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=False,
        max_age=604800, 
        samesite="none",
        secure=True,
        path="/"
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
    
    response.set_cookie(key="access_token", value=new_access_token, httponly=False, max_age=3600, samesite="none", secure=True, path="/")
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=False, max_age=604800, samesite="none", secure=True, path="/")
    
    return {"message": "Token refreshed"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token", samesite="none", secure=True, path="/")
    response.delete_cookie(key="refresh_token", samesite="none", secure=True, path="/")
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    current_user["_id"] = str(current_user["_id"])
    if "studio_id" in current_user and current_user["studio_id"]:
        current_user["studio_id"] = str(current_user["studio_id"])
    return current_user
