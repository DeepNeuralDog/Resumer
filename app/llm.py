"""LLM client setup and ATS optimization functions."""
from typing import List, Optional

from fastapi import HTTPException
from anthropic import AsyncAnthropicFoundry
import instructor
from instructor import Instructor

from app.config import settings
from app.models import Skill, Experience, Project, ATSResumeData, ATSGapsResponse
from app import database as db


# LLM Prompts
PROMPT_GAPS = """
You are an ATS resume assistant.
Given a job description and the user's existing skills/experience/projects,
return ONLY a list of missing skills the user likely lacks.
Return JSON with key: missing_skills (array of strings).
Do not include skills already present.
"""

PROMPT_FINAL = """
You are an ATS optimized Resume Assistant. Given:
- A job description
- A user's skills/experience/projects (from their DB)
- A list of user-confirmed additional skills (the user claims they have)

Pick the most relevant items and rewrite bullets to match the job description.
Be as direct and concise as possible.
Do not add any skills/experience/projects the user doesn't have.
Only include user-confirmed additional skills.
"""


# Global client reference (set during app startup)
_anthropic_client: Optional[Instructor] = None


def init_llm_client() -> Optional[Instructor]:
    """Initialize the Anthropic LLM client."""
    global _anthropic_client
    
    if not settings.has_llm_config:
        return None
    
    try:
        client = AsyncAnthropicFoundry(
            api_key=settings.LLM_API_KEY_ANTHROPIC,
            base_url=settings.LLM_API_ENDPOINT_ANTHROPIC,
        )
        _anthropic_client = instructor.from_anthropic(client)
        return _anthropic_client
    except Exception as e:
        _anthropic_client = None
        raise RuntimeError(f"Failed to initialize Anthropic client: {e}") from e


def get_llm_client() -> Optional[Instructor]:
    """Get the LLM client instance."""
    return _anthropic_client


def fetch_user_skills(conn, user_id: int) -> List[Skill]:
    """Fetch all skills for a user as Skill models."""
    skills_data = db.get_skills(conn, user_id)
    return [
        Skill(
            skill_name=s["skill_name"],
            bullet_points=s.get("bullet_points", [])
        )
        for s in skills_data
    ]


def fetch_user_experiences(conn, user_id: int) -> List[Experience]:
    """Fetch all experiences for a user as Experience models."""
    exps_data = db.get_experiences(conn, user_id)
    return [
        Experience(
            experience_name=e["experience_name"],
            bullet_points=e.get("bullet_points", []),
            start_year=e.get("start_year"),
            end_year=e.get("end_year")
        )
        for e in exps_data
    ]


def fetch_user_projects(conn, user_id: int) -> List[Project]:
    """Fetch all projects for a user as Project models."""
    projs_data = db.get_projects(conn, user_id)
    return [
        Project(
            project_name=p["project_name"],
            bullet_points=p.get("bullet_points", []),
            github_link=p.get("github_link")
        )
        for p in projs_data
    ]


async def run_ats_gaps(job_description: str, user_id: int) -> ATSGapsResponse:
    """Run ATS gaps analysis to find missing skills."""
    client = get_llm_client()
    
    if not client:
        raise HTTPException(status_code=503, detail="LLM client not configured")
    
    with db.get_db() as conn:
        skills = fetch_user_skills(conn, user_id)
        experience = fetch_user_experiences(conn, user_id)
        projects = fetch_user_projects(conn, user_id)
    
    input_str = f"Job Description:\n{job_description}\n\n"
    input_str += "User's Skills:\n"
    for skill in skills:
        input_str += skill.to_ai_context_string() + "\n"
    input_str += "\nUser's Experience:\n"
    for exp in experience:
        input_str += exp.to_ai_context_string() + "\n"
    input_str += "\nUser's Projects:\n"
    for proj in projects:
        input_str += proj.to_ai_context_string() + "\n"
    
    try:
        response = await client.completions.create(
            model=settings.LLM_DEPLOYMENT_NAME_ANTHROPIC,
            messages=[
                {"role": "system", "content": PROMPT_GAPS},
                {"role": "user", "content": input_str}
            ],
            max_tokens=1000,
            response_model=ATSGapsResponse,
        )
        return ATSGapsResponse.model_validate(response)
    except Exception as e:
        print("LLM ERROR:", str(e))
        raise HTTPException(status_code=500, detail=f"LLM processing error: {str(e)}")


async def run_ats_optimization(
    job_description: str, 
    user_id: int, 
    selected_missing_skills: Optional[List[str]] = None
) -> ATSResumeData:
    """Run ATS optimization to tailor resume for a job."""
    client = get_llm_client()
    
    if not client:
        raise HTTPException(status_code=503, detail="LLM client not configured")
    
    with db.get_db() as conn:
        skills = fetch_user_skills(conn, user_id)
        experience = fetch_user_experiences(conn, user_id)
        projects = fetch_user_projects(conn, user_id)
    
    input_str = f"Job Description:\n{job_description}\n\n"
    input_str += "User's Skills:\n"
    for skill in skills:
        input_str += skill.to_ai_context_string() + "\n"
    input_str += "\nUser's Experience: (Note: You must copy paste the experience from here which are relevant to the job description)\n"
    for exp in experience:
        input_str += exp.to_ai_context_string() + "\n"
    input_str += "\nUser's Projects: (Note: You must copy paste the projects from here which are relevant to the job description)\n"
    for proj in projects:
        input_str += proj.to_ai_context_string() + "\n"
    
    if selected_missing_skills:
        input_str += "\nUser-Confirmed Additional Skills: (Note: Also create bullet points for these skills and add those bullet points in relevent skill category. You can also create new skill categories if the bullet points do not fit in existing categories)\n"
        for skill in selected_missing_skills:
            input_str += f"- {skill}\n"
    
    try:
        response = await client.completions.create(
            model=settings.LLM_DEPLOYMENT_NAME_ANTHROPIC,
            messages=[
                {"role": "system", "content": PROMPT_FINAL},
                {"role": "user", "content": input_str}
            ],
            max_tokens=3000,
            response_model=ATSResumeData,
        )
        return ATSResumeData.model_validate(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing error: {str(e)}")
