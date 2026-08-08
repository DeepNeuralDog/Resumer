"""Education CRUD routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Education
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["educations"])


@router.get("/educations")
def get_educations(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all education entries for the current user."""
    with db.get_db() as conn:
        educations = db.get_educations(conn, user["id"], query=q)
    return educations


@router.post("/educations", status_code=status.HTTP_201_CREATED)
def create_education(
    edu_data: Education,
    user: dict = Depends(get_current_user)
):
    """Create a new education entry."""
    with db.get_db() as conn:
        existing = db.get_education_by_details(
            conn,
            edu_data.education_name,
            edu_data.institution,
            edu_data.start,
            edu_data.end,
            edu_data.grade,
            user["id"]
        )
        if existing:
            raise HTTPException(status_code=409, detail="Education already exists.")

        edu_id = db.create_education(
            conn,
            edu_data.education_name,
            edu_data.institution,
            user["id"],
            edu_data.start,
            edu_data.end,
            edu_data.grade
        )
        
        edu = db.get_education_by_id(conn, edu_id, user["id"])
    
    return edu


@router.put("/educations/{education_id}")
def update_education(
    education_id: int,
    edu_data: Education,
    user: dict = Depends(get_current_user)
):
    """Update an education entry."""
    with db.get_db() as conn:
        edu = db.get_education_by_id(conn, education_id, user["id"])
        if not edu:
            raise HTTPException(status_code=404, detail="Education not found")

        db.update_education(
            conn,
            education_id,
            edu_data.education_name,
            edu_data.institution,
            edu_data.start,
            edu_data.end,
            edu_data.grade
        )
        
        updated = db.get_education_by_id(conn, education_id, user["id"])
    
    return updated


@router.delete("/educations/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_education(
    education_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete an education entry."""
    with db.get_db() as conn:
        edu = db.get_education_by_id(conn, education_id, user["id"])
        if not edu:
            raise HTTPException(status_code=404, detail="Education not found")

        db.delete_education(conn, education_id)
    return
