"""Projects CRUD routes."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import Project
from app.auth import get_current_user
from app import database as db


router = APIRouter(prefix="/api", tags=["projects"])


@router.get("/projects")
def get_projects(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get all projects for the current user."""
    with db.get_db() as conn:
        projects = db.get_projects(conn, user["id"], query=q)
    
    return [
        {
            "id": p["id"],
            "project_name": p["project_name"],
            "github_link": p.get("github_link"),
            "bullet_points": p.get("bullet_points", [])
        }
        for p in projects
    ]


@router.get("/projects/{project_id}/bullets")
def get_project_bullets(
    project_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get bullets for a specific project."""
    with db.get_db() as conn:
        project = db.get_project_by_id(conn, project_id, user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        bullets = db.get_project_bullets(conn, project_id, query=q)
    
    return bullets


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: Project,
    user: dict = Depends(get_current_user)
):
    """Create a new project."""
    with db.get_db() as conn:
        existing = db.get_project_by_details(
            conn,
            project_data.project_name,
            project_data.github_link,
            user["id"]
        )
        if existing:
            raise HTTPException(status_code=409, detail="Project already exists.")

        project_id = db.create_project(
            conn,
            project_data.project_name,
            user["id"],
            project_data.github_link,
            project_data.bullet_points
        )
        
        bullets = db.get_project_bullets(conn, project_id)
    
    return {
        "id": project_id,
        "project_name": project_data.project_name,
        "github_link": project_data.github_link,
        "bullet_points": bullets
    }


@router.put("/projects/{project_id}")
def update_project(
    project_id: int,
    project_data: Project,
    user: dict = Depends(get_current_user)
):
    """Update a project."""
    with db.get_db() as conn:
        project = db.get_project_by_id(conn, project_id, user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        db.update_project(
            conn,
            project_id,
            project_data.project_name,
            project_data.github_link,
            project_data.bullet_points
        )
        
        bullets = db.get_project_bullets(conn, project_id)
    
    return {
        "id": project_id,
        "project_name": project_data.project_name,
        "github_link": project_data.github_link,
        "bullet_points": bullets
    }


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    user: dict = Depends(get_current_user)
):
    """Delete a project."""
    with db.get_db() as conn:
        project = db.get_project_by_id(conn, project_id, user["id"])
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        db.delete_project(conn, project_id)
    return
