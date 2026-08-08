"""ATS optimization routes."""
from fastapi import APIRouter, Depends

from app.models import ATSOptimizeRequest
from app.auth import get_current_user
from app.llm import run_ats_gaps, run_ats_optimization


router = APIRouter(prefix="/api", tags=["ats"])


@router.post("/ats-gaps")
async def ats_gaps(
    payload: ATSOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    """Analyze job description to find skill gaps."""
    gaps = await run_ats_gaps(payload.job_description, user["id"])
    return gaps


@router.post("/ats-optimize")
async def ats_optimize(
    payload: ATSOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    """Optimize resume for a specific job description."""
    ats_data = await run_ats_optimization(
        payload.job_description,
        user["id"],
        selected_missing_skills=payload.selected_missing_skills
    )
    return ats_data
