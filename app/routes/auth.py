"""Authentication routes: register, login, logout."""
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.config import settings
from app.models import UserCreate, UserLogin
from app.auth import get_password_hash, create_access_token, authenticate_user
from app import database as db


router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register")
def register_user(user_data: UserCreate):
    """Register a new user."""
    with db.get_db() as conn:
        existing = db.get_user_by_email(conn, user_data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_password = get_password_hash(user_data.password)
        db.create_user(
            conn,
            name=user_data.name,
            email=user_data.email,
            password_hash=hashed_password,
            phone=user_data.phone,
            location=user_data.location,
            linkedin=user_data.linkedin,
            github=user_data.github,
            website=user_data.website
        )

    return {"message": "User registered successfully"}


@router.post("/login")
def login(user_data: UserLogin):
    """Login and get access token."""
    user = authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )

    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    return response


@router.get("/logout")
def logout():
    """Logout and clear access token."""
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response
