"""Experiences CRUD routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Experience
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["experiences"])


@router.get("/experiences")
def get_experiences(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all experiences for the current user."""
    with db.get_db() as conn:
        experiences = db.get_experiences(conn, user["id"], query=q)
    
    return [
        {
            "id": e["id"],
            "experience_name": e["experience_name"],
            "start_year": e.get("start_year"),
            "end_year": e.get("end_year"),
            "bullet_points": e.get("bullet_points", [])
        }
        for e in experiences
    ]


@router.get("/experiences/{experience_id}/bullets")
def get_experience_bullets(
    experience_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get bullets for a specific experience."""
    with db.get_db() as conn:
        exp = db.get_experience_by_id(conn, experience_id, user["id"])
        if not exp:
            raise HTTPException(status_code=404, detail="Experience not found")
        
        bullets = db.get_experience_bullets(conn, experience_id, query=q)
    
    return bullets


@router.post("/experiences", status_code=status.HTTP_201_CREATED)
def create_experience(
    exp_data: Experience,
    user: dict = Depends(get_current_user)
):
    """Create a new experience."""
    with db.get_db() as conn:
        existing = db.get_experience_by_details(
            conn, 
            exp_data.experience_name,
            exp_data.start_year,
            exp_data.end_year,
            user["id"]
        )
        if existing:
            raise HTTPException(status_code=409, detail="Experience already exists.")

        exp_id = db.create_experience(
            conn,
            exp_data.experience_name,
            user["id"],
            exp_data.start_year,
            exp_data.end_year,
            exp_data.bullet_points
        )
        
        bullets = db.get_experience_bullets(conn, exp_id)
    
    return {
        "id": exp_id,
        "experience_name": exp_data.experience_name,
        "start_year": exp_data.start_year,
        "end_year": exp_data.end_year,
        "bullet_points": bullets
    }


@router.put("/experiences/{experience_id}")
def update_experience(
    experience_id: int,
    exp_data: Experience,
    user: dict = Depends(get_current_user)
):
    """Update an experience."""
    with db.get_db() as conn:
        exp = db.get_experience_by_id(conn, experience_id, user["id"])
        if not exp:
            raise HTTPException(status_code=404, detail="Experience not found")

        db.update_experience(
            conn,
            experience_id,
            exp_data.experience_name,
            exp_data.start_year,
            exp_data.end_year,
            exp_data.bullet_points
        )
        
        bullets = db.get_experience_bullets(conn, experience_id)
    
    return {
        "id": experience_id,
        "experience_name": exp_data.experience_name,
        "start_year": exp_data.start_year,
        "end_year": exp_data.end_year,
        "bullet_points": bullets
    }


@router.delete("/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experience(
    experience_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete an experience."""
    with db.get_db() as conn:
        exp = db.get_experience_by_id(conn, experience_id, user["id"])
        if not exp:
            raise HTTPException(status_code=404, detail="Experience not found")

        db.delete_experience(conn, experience_id)
    return
