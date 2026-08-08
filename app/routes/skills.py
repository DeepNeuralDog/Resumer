"""Skills CRUD routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Skill
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/skills")
def get_skills(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all skills for the current user."""
    with db.get_db() as conn:
        skills = db.get_skills(conn, user["id"], query=q)
    
    return [
        {
            "id": s["id"],
            "skill_name": s["skill_name"],
            "bullet_points": s.get("bullet_points", [])
        }
        for s in skills
    ]


@router.get("/skills_with_bullets")
def get_skills_with_bullets(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all skills with bullets for the current user."""
    return get_skills(q=q, user=user)


@router.get("/skills/{skill_id}/bullets")
def get_skill_bullets(
    skill_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get bullets for a specific skill."""
    with db.get_db() as conn:
        skill = db.get_skill_by_id(conn, skill_id, user["id"])
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        
        bullets = db.get_skill_bullets(conn, skill_id, query=q)
    
    return bullets


@router.post("/skills", status_code=status.HTTP_201_CREATED)
def create_skill(
    skill_data: Skill,
    user: dict = Depends(get_current_user)
):
    """Create a new skill."""
    with db.get_db() as conn:
        existing = db.get_skill_by_name(conn, skill_data.skill_name, user["id"])
        if existing:
            raise HTTPException(status_code=409, detail="A skill with this name already exists.")

        skill_id = db.create_skill(
            conn, 
            skill_data.skill_name, 
            user["id"], 
            skill_data.bullet_points
        )
        
        bullets = db.get_skill_bullets(conn, skill_id)
    
    return {
        "id": skill_id,
        "skill_name": skill_data.skill_name,
        "bullet_points": bullets
    }


@router.put("/skills/{skill_id}")
def update_skill(
    skill_id: int,
    skill_data: Skill,
    user: dict = Depends(get_current_user)
):
    """Update a skill."""
    with db.get_db() as conn:
        skill = db.get_skill_by_id(conn, skill_id, user["id"])
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        db.update_skill(conn, skill_id, skill_data.skill_name, skill_data.bullet_points)
        
        bullets = db.get_skill_bullets(conn, skill_id)
    
    return {
        "id": skill_id,
        "skill_name": skill_data.skill_name,
        "bullet_points": bullets
    }


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete a skill."""
    with db.get_db() as conn:
        skill = db.get_skill_by_id(conn, skill_id, user["id"])
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")

        db.delete_skill(conn, skill_id)
    return
