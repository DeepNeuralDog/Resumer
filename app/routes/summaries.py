"""Summaries CRUD routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import SummaryModel
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["summaries"])


@router.get("/summaries")
def get_summaries(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    """Get all summaries for the current user."""
    with db.get_db() as conn:
        summaries = db.get_summaries(conn, user["id"], query=q)
    return [s["text"] for s in summaries]


@router.get("/summaries_with_ids")
def get_summaries_with_ids(user: dict = Depends(get_current_user)):
    """Get all summaries with IDs for the current user."""
    with db.get_db() as conn:
        summaries = db.get_summaries(conn, user["id"])
    return [{"id": s["id"], "text": s["text"]} for s in summaries]


@router.post("/summaries", status_code=status.HTTP_201_CREATED)
def create_summary(
    summary_data: SummaryModel,
    user: dict = Depends(get_current_user)
):
    """Create a new summary."""
    with db.get_db() as conn:
        existing = db.get_summary_by_text(conn, summary_data.text, user["id"])
        if existing:
            raise HTTPException(status_code=409, detail="Summary already exists.")

        summary_id = db.create_summary(conn, summary_data.text, user["id"])
    
    return {"id": summary_id, "text": summary_data.text}


@router.put("/summaries/{summary_id}")
def update_summary(
    summary_id: int,
    summary_data: SummaryModel,
    user: dict = Depends(get_current_user)
):
    """Update a summary."""
    with db.get_db() as conn:
        existing = db.get_summary_by_id(conn, summary_id, user["id"])
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found")

        db.update_summary(conn, summary_id, summary_data.text)
    
    return {"id": summary_id, "text": summary_data.text}


@router.delete("/summaries/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_summary(
    summary_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete a summary."""
    with db.get_db() as conn:
        existing = db.get_summary_by_id(conn, summary_id, user["id"])
        if not existing:
            raise HTTPException(status_code=404, detail="Summary not found")

        db.delete_summary(conn, summary_id)
    return
