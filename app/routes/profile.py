"""User profile routes."""
from fastapi import APIRouter, Depends

from app.models import UserCreate
from app.auth import get_current_user, get_password_hash
from app import database as db


router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/user-profile")
def get_user_profile(user: dict = Depends(get_current_user)):
    """Get current user's profile."""
    return {
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "location": user["location"],
        "linkedin": user["linkedin"],
        "github": user["github"],
        "website": user["website"]
    }


@router.put("/user-profile")
def update_user_profile(
    user_data: UserCreate,
    user: dict = Depends(get_current_user)
):
    """Update current user's profile."""
    with db.get_db() as conn:
        password_hash = None
        if user_data.password:
            password_hash = get_password_hash(user_data.password)
        
        db.update_user(
            conn,
            user_id=user["id"],
            name=user_data.name,
            email=user_data.email,
            phone=user_data.phone,
            location=user_data.location,
            linkedin=user_data.linkedin,
            github=user_data.github,
            website=user_data.website,
            password_hash=password_hash
        )
        
        updated = db.get_user_by_id(conn, user["id"])
    
    return {
        "name": updated["name"],
        "email": updated["email"],
        "phone": updated["phone"],
        "location": updated["location"],
        "linkedin": updated["linkedin"],
        "github": updated["github"],
        "website": updated["website"]
    }
