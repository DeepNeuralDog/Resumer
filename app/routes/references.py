"""References CRUD routes."""
from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Reference
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["references"])


@router.get("/references")
def get_references(user: dict = Depends(get_current_user)):
    """Get all references for the current user."""
    with db.get_db() as conn:
        references = db.get_references(conn, user["id"])
    return references


@router.post("/references", status_code=status.HTTP_201_CREATED)
def create_reference(
    ref_data: Reference,
    user: dict = Depends(get_current_user)
):
    """Create a new reference."""
    with db.get_db() as conn:
        existing = db.get_reference_by_details(
            conn,
            ref_data.referer_name,
            ref_data.referer_institute,
            ref_data.position,
            ref_data.connection_type,
            ref_data.institution_url,
            user["id"]
        )
        if existing:
            raise HTTPException(status_code=409, detail="Reference already exists.")

        ref_id = db.create_reference(
            conn,
            ref_data.referer_name,
            ref_data.referer_institute,
            user["id"],
            ref_data.position,
            ref_data.connection_type,
            ref_data.institution_url
        )
        
        ref = db.get_reference_by_id(conn, ref_id, user["id"])
    
    return ref


@router.put("/references/{reference_id}")
def update_reference(
    reference_id: int,
    ref_data: Reference,
    user: dict = Depends(get_current_user)
):
    """Update a reference."""
    with db.get_db() as conn:
        ref = db.get_reference_by_id(conn, reference_id, user["id"])
        if not ref:
            raise HTTPException(status_code=404, detail="Reference not found")

        db.update_reference(
            conn,
            reference_id,
            ref_data.referer_name,
            ref_data.referer_institute,
            ref_data.position,
            ref_data.connection_type,
            ref_data.institution_url
        )
        
        updated = db.get_reference_by_id(conn, reference_id, user["id"])
    
    return updated


@router.delete("/references/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    reference_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete a reference."""
    with db.get_db() as conn:
        ref = db.get_reference_by_id(conn, reference_id, user["id"])
        if not ref:
            raise HTTPException(status_code=404, detail="Reference not found")

        db.delete_reference(conn, reference_id)
    return
