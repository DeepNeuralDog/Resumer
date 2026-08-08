"""PDF generation routes - returns rendered HTML for client-side PDF."""
import os
import base64
import io
import logging
from typing import List

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import jinja2
from PIL import Image

from app.models import ResumeData, Experience, Education
from app.auth import get_current_user
from app.llm import run_ats_optimization, get_llm_client
from app import database as db


router = APIRouter(tags=["pdf"])

TEMPLATE_DIR = "html_templates"


def save_resume_data(conn, data: ResumeData, user_id: int):
    """Save resume data to database (skills, experience, projects, etc.)"""
    # Save summary if provided
    if data.summary and data.summary.strip():
        existing_summary = db.get_summary_by_text(conn, data.summary, user_id)
        if not existing_summary:
            db.create_summary(conn, data.summary, user_id)

    # Save skills
    for skill_data in data.skills:
        if skill_data.skill_name and skill_data.skill_name.strip():
            existing_skill = db.get_skill_by_name(conn, skill_data.skill_name, user_id)
            if not existing_skill:
                db.create_skill(conn, skill_data.skill_name, user_id, skill_data.bullet_points)

    # Save experiences
    for exp_data in data.experience:
        if exp_data.experience_name and exp_data.experience_name.strip():
            existing_exp = db.get_experience_by_details(
                conn, exp_data.experience_name, exp_data.start_year, exp_data.end_year, user_id
            )
            if not existing_exp:
                db.create_experience(
                    conn, exp_data.experience_name, user_id,
                    exp_data.start_year, exp_data.end_year, exp_data.bullet_points
                )

    # Save projects
    for proj_data in data.projects:
        if proj_data.project_name and proj_data.project_name.strip():
            existing_proj = db.get_project_by_details(
                conn, proj_data.project_name, proj_data.github_link, user_id
            )
            if not existing_proj:
                db.create_project(
                    conn, proj_data.project_name, user_id,
                    proj_data.github_link, proj_data.bullet_points
                )

    # Save education
    for edu_data in data.education:
        if edu_data.education_name and edu_data.education_name.strip():
            existing_edu = db.get_education_by_details(
                conn, edu_data.education_name, edu_data.institution,
                edu_data.start, edu_data.end, edu_data.grade, user_id
            )
            if not existing_edu:
                db.create_education(
                    conn, edu_data.education_name, edu_data.institution, user_id,
                    edu_data.start, edu_data.end, edu_data.grade
                )

    # Save references
    for ref_data in data.references:
        if ref_data.referer_name and ref_data.referer_name.strip():
            existing_ref = db.get_reference_by_details(
                conn, ref_data.referer_name, ref_data.referer_institute,
                ref_data.position, ref_data.connection_type, ref_data.institution_url, user_id
            )
            if not existing_ref:
                db.create_reference(
                    conn, ref_data.referer_name, ref_data.referer_institute, user_id,
                    ref_data.position, ref_data.connection_type, ref_data.institution_url
                )


@router.post("/generate-pdf")
async def generate_pdf(
    data: ResumeData,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """
    Generate resume HTML for client-side PDF conversion.
    Returns rendered HTML that frontend converts to PDF using html2pdf.js
    """
    try:
        # Run ATS optimization if job description provided and LLM available
        if data.job_description and get_llm_client():
            ats_data = await run_ats_optimization(data.job_description, user["id"])
            data.summary = ats_data.summary
            data.skills = ats_data.skills
            data.experience = ats_data.experience
            data.projects = ats_data.projects

        # Save resume data to database
        with db.get_db() as conn:
            save_resume_data(conn, data, user["id"])

        template_name = request.headers.get("X-Template-Name", "basic_resume.html")
        template_path = os.path.join(TEMPLATE_DIR, template_name)

        if not os.path.exists(template_path):
            return JSONResponse({"error": f"Template '{template_name}' not found."}, status_code=404)

        # Set up Jinja2 environment for HTML templates
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
            autoescape=True
        )
        template = env.get_template(template_name)

        # Process profile image to base64 data URI if provided
        image_data_uri = None
        if data.image_base64:
            try:
                if ',' in data.image_base64:
                    image_data_b64 = data.image_base64.split(',', 1)[1]
                else:
                    image_data_b64 = data.image_base64

                image_data = base64.b64decode(image_data_b64)
                image = Image.open(io.BytesIO(image_data))

                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB')
                elif image.mode != 'RGB':
                    image = image.convert('RGB')

                # Convert back to base64 for embedding in HTML
                buffered = io.BytesIO()
                image.save(buffered, format="PNG", optimize=True)
                image_data_uri = f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"

            except Exception as e:
                logging.error(f"Error processing image: {e}")

        # Update contact info from user data
        contact_data = {
            "email": data.contact.email or user["email"],
            "phone": data.contact.phone or user["phone"],
            "location": data.contact.location or user["location"],
            "linkedin": data.contact.linkedin or user["linkedin"],
            "github": data.contact.github or user["github"],
            "website": data.contact.website or user["website"]
        }

        # Sanitize experience and education dates
        sanitized_exp: List[Experience] = []
        sanitized_edu: List[Education] = []

        for exp in data.experience:
            if exp.end_year == "":
                new_exp = Experience(
                    experience_name=exp.experience_name,
                    bullet_points=exp.bullet_points,
                    start_year=exp.start_year,
                    end_year="Present"
                )
                sanitized_exp.append(new_exp)
            else:
                sanitized_exp.append(exp)

        for edu in data.education:
            if edu.end == "":
                new_edu = Education(
                    education_name=edu.education_name,
                    institution=edu.institution,
                    start=edu.start,
                    grade=edu.grade,
                    end="Present",
                )
                sanitized_edu.append(new_edu)
            else:
                sanitized_edu.append(edu)

        data.experience = sanitized_exp
        data.education = sanitized_edu

        # Render HTML template
        html_content = template.render(
            name=data.name or user["name"],
            contact=contact_data,
            summary=data.summary,
            image_data_uri=image_data_uri,
            skills=[s.model_dump() for s in data.skills],
            experience=[e.model_dump() for e in data.experience],
            projects=[p.model_dump() for p in data.projects],
            education=[e.model_dump() for e in data.education],
            references=[r.model_dump() for r in data.references]
        )

        # Return HTML for client-side PDF generation
        return JSONResponse({
            "html": html_content,
            "filename": "resume.pdf"
        })

    except Exception as e:
        import traceback
        logging.error(f"SERVER ERROR: {traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/save-json")
async def save_json(
    data: ResumeData,
    user: dict = Depends(get_current_user)
):
    """Save resume data without generating PDF."""
    with db.get_db() as conn:
        save_resume_data(conn, data, user["id"])
    
    response_data = data.model_dump()
    response_data["image_base64"] = None
    return JSONResponse(response_data)


@router.get("/templates")
def list_templates():
    """List available resume templates."""
    try:
        templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".html")]
        return JSONResponse(templates)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
