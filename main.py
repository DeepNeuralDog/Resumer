from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from tempfile import NamedTemporaryFile
from typing import List, Optional
from pydantic import BaseModel, Field
from PIL import Image
import os
import shutil
import jinja2
import base64
import io
import json
import time
import logging
import subprocess
import database as db
from database import engine, create_db_and_tables
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import AsyncAzureOpenAI
from anthropic import AsyncAnthropicFoundry
import instructor
from instructor import Instructor

load_dotenv()

app = FastAPI()

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

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    await engine.start_connection_pool()

    api_key = os.getenv("LLM_API_KEY_ANTHROPIC")
    endpoint = os.getenv("LLM_API_ENDPOINT_ANTHROPIC")

    if all([api_key, endpoint]):
            
        try:

            client = AsyncAnthropicFoundry(
                    api_key=api_key,
                    base_url=endpoint,
                )

            client = instructor.from_anthropic(client)
            app.state.anthropic_client = client


        except Exception as e:
            app.state.anthropic_client = None
            raise RuntimeError("Failed to initialize Anthropic client. ATS optimization will be unavailable.") from e
    else:
        app.state.anthropic_client = None
        raise RuntimeError("Anthropic LLM client configuration is missing. ATS optimization will be unavailable.")

@app.on_event("shutdown")
async def on_shutdown():
    await engine.close_connection_pool()
    
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_DIR = "typst_templates"


# User models
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None


class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class SummaryModel(BaseModel):
    text: str


class Skill(BaseModel):
    skill_name: str = Field(description="Name of the Skill Group/Category. This describes a category of skills which are related.")
    bullet_points: List[str] = Field(description="List of bullet points describing the skill category")

    def to_ai_context_string(self) -> str:
        bullets_str = "Skill_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Skill Catetory:  {self.skill_name}:\n{bullets_str}"

class Experience(BaseModel):
    experience_name: str = Field(description="Name of the Experience")
    bullet_points: List[str] = Field(description="List of bullet points describing the experience")
    start_year: Optional[str] = None
    end_year: Optional[str] = None

    def to_ai_context_string(self) -> str:
        bullets_str = "Experience_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Experience:  {self.experience_name} (From {self.start_year} to {self.end_year}):\n{bullets_str}"


class Project(BaseModel):
    project_name: str = Field(description="Name of the Project")
    bullet_points: List[str] = Field(description="List of bullet points describing the project")
    github_link: Optional[str] = None

    def to_ai_context_string(self) -> str:
        bullets_str = "Project_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Project:  {self.project_name} (GitHub: {self.github_link}):\n{bullets_str}"


class Education(BaseModel):
    education_name: str
    institution: str
    start: Optional[str] = None
    end: Optional[str] = None
    grade: Optional[str] = None


class Reference(BaseModel):
    referer_name: str
    referer_institute: str
    position: Optional[str] = None
    connection_type: Optional[str] = None
    institution_url: Optional[str] = None


class ResumeData(BaseModel):
    name: str
    contact: Contact
    summary: Optional[str] = None
    image_base64: Optional[str] = None
    skills: List[Skill]
    experience: List[Experience]
    projects: List[Project]
    education: List[Education]
    references: List[Reference]
    job_description: Optional[str] = None



class ATSResumeData(BaseModel):
    summary: str = Field(description="The optimized summery which fits the job description. Must be as concise as possible.")
    skills: List[Skill] = Field(description="List of Skills optimized for the job description. Don't add any skills which I don't have.")
    experience: List[Experience] = Field(description="List of Experience optimized for the job description. Don't add any experience which I don't have.")
    projects: List[Project] = Field(description="List of optimized projects for the job description. Don't add any projects which I don't have or which are not relevant.")

class ATSGapsResponse(BaseModel):
    missing_skills: List[str] = Field(default_factory=list)


class ATSOptimizeRequest(BaseModel):
    job_description: str
    selected_missing_skills: Optional[List[str]] = None



async def fetch_user_skills(user_id: int) -> List[Skill]:
    skills = await db.Skill.select().where(db.Skill.user == user_id).run()
    results: List[Skill] = []
    for s in skills:
        bullets = await db.SkillBullet.select(db.SkillBullet.text).where(db.SkillBullet.skill == s["id"]).run()
        results.append(Skill(
            skill_name=s["skill_name"],
            bullet_points=[b["text"] for b in bullets]
        ))
    return results


async def fetch_user_experience(user_id: int) -> List[Experience]:
    exps = await db.Experience.select().where(db.Experience.user == user_id).run()
    results: List[Experience] = []
    for e in exps:
        bullets = await db.ExperienceBullet.select(db.ExperienceBullet.text).where(db.ExperienceBullet.experience == e["id"]).run()
        results.append(Experience(
            experience_name=e["experience_name"],
            bullet_points=[b["text"] for b in bullets],
            start_year=e["start_year"],
            end_year=e["end_year"]
        ))
    return results


async def fetch_user_projects(user_id: int) -> List[Project]:
    projs = await db.Project.select().where(db.Project.user == user_id).run()
    results: List[Project] = []
    for p in projs:
        bullets = await db.ProjectBullet.select(db.ProjectBullet.text).where(db.ProjectBullet.project == p["id"]).run()
        results.append(Project(
            project_name=p["project_name"],
            bullet_points=[b["text"] for b in bullets],
            github_link=p["github_link"]
        ))
    return results


async def run_ats_optimization(job_description: str, user_id: int, selected_missing_skills: Optional[List[str]] = None) -> ATSResumeData:
    client : Instructor = app.state.anthropic_client
    deployment = os.getenv("LLM_DEPLOYMENT_NAME_ANTHROPIC")

    if not client:
        raise HTTPException(status_code=503, detail="LLM client not configured")

    skills = await fetch_user_skills(user_id)
    experience = await fetch_user_experience(user_id)
    projects = await fetch_user_projects(user_id)

    input_str = ""
    input_str += f"Job Description:\n{job_description}\n\n"
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
            model=deployment,
            messages=[
                {"role": "system", "content": PROMPT_FINAL},
                {"role": "user", "content": input_str}
            ],
            max_tokens=3000,
            response_model=ATSResumeData,
        )

        content = ATSResumeData.model_validate(response)
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM processing error: {str(e)}")


async def run_ats_gaps(job_description: str, user_id: int) -> ATSGapsResponse:
    client : Instructor = app.state.anthropic_client
    deployment = os.getenv("LLM_DEPLOYMENT_NAME_ANTHROPIC")

    if not client:
        raise HTTPException(status_code=503, detail="LLM client not configured")

    skills = await fetch_user_skills(user_id)
    experience = await fetch_user_experience(user_id)
    projects = await fetch_user_projects(user_id)

    input_str = ""
    input_str += f"Job Description:\n{job_description}\n\n"
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
            model=deployment,
            messages=[
                {"role": "system", "content": PROMPT_FINAL},
                {"role": "user", "content": input_str}
            ],
            max_tokens=1000,
            response_model=ATSGapsResponse,
        )

        content = ATSGapsResponse.model_validate(response)
        return content
    except Exception as e:
        print("LLM ERROR:", str(e))
        raise HTTPException(status_code=500, detail=f"LLM processing error: {str(e)}")



def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def fetch_one(query):
    rows = await query.run()
    return rows[0] if rows else None


async def authenticate_user(email: str, password: str):
    user = await fetch_one(
        db.User.select().where(db.User.email == email)
    )
    if not user:
        return False
    if not verify_password(password, user["password_hash"]):
        return False
    return user


async def get_current_user(request: Request):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split("Bearer ")[1]
        else:
            raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await fetch_one(
        db.User.select().where(db.User.id == user_id)
    )
    if user is None:
        raise credentials_exception
    return user


def py_to_typst(val):
    if isinstance(val, str):
        return '"' + val.replace('\\\\', '\\\\\\\\').replace('"', '\\\\"') + '"'
    elif isinstance(val, bool):
        return 'true' if val else 'false'
    elif val is None:
        return 'none'
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        if not val:
            return '()'
        processed_items = [py_to_typst(v) for v in val]
        items_str = ', '.join(processed_items)
        if len(processed_items) == 1:
            return f'({items_str},)'
        else:
            return f'({items_str})'
    elif isinstance(val, dict):
        if not val:
            return '(:)'
        return '(' + ', '.join(f'{k}: {py_to_typst(v)}' for k, v in val.items()) + ')'
    else:
        return 'none'
async def save_resume_data(data: ResumeData, user_id: int):
    if data.summary and data.summary.strip():
        existing_summary = await fetch_one(
            db.Summary.select().where(
                (db.Summary.text == data.summary) &
                (db.Summary.user == user_id)
            )
        )
        if not existing_summary:
            await db.Summary.insert(
                db.Summary(text=data.summary, user=user_id)
            ).run()

    for skill_data in data.skills:
        if skill_data.skill_name and skill_data.skill_name.strip():
            existing_skill = await fetch_one(
                db.Skill.select().where(
                    (db.Skill.skill_name == skill_data.skill_name) &
                    (db.Skill.user == user_id)
                )
            )
            if not existing_skill:
                await db.Skill.insert(
                    db.Skill(skill_name=skill_data.skill_name, user=user_id)
                ).run()

            skill = await fetch_one(
                db.Skill.select().where(
                    (db.Skill.skill_name == skill_data.skill_name) &
                    (db.Skill.user == user_id)
                )
            )

            if skill:
                for point in skill_data.bullet_points:
                    if point and point.strip():
                        existing_bullet = await fetch_one(
                            db.SkillBullet.select().where(
                                (db.SkillBullet.text == point) &
                                (db.SkillBullet.skill == skill["id"])
                            )
                        )
                        if not existing_bullet:
                            await db.SkillBullet.insert(
                                db.SkillBullet(text=point, skill=skill["id"])
                            ).run()

    for exp_data in data.experience:
        if exp_data.experience_name and exp_data.experience_name.strip():
            existing_exp = await fetch_one(
                db.Experience.select().where(
                    (db.Experience.experience_name == exp_data.experience_name) &
                    (db.Experience.start_year == exp_data.start_year) &
                    (db.Experience.end_year == exp_data.end_year) &
                    (db.Experience.user == user_id)
                )
            )
            if not existing_exp:
                await db.Experience.insert(
                    db.Experience(
                        experience_name=exp_data.experience_name,
                        start_year=exp_data.start_year,
                        end_year=exp_data.end_year,
                        user=user_id
                    )
                ).run()

            exp = await fetch_one(
                db.Experience.select().where(
                    (db.Experience.experience_name == exp_data.experience_name) &
                    (db.Experience.start_year == exp_data.start_year) &
                    (db.Experience.end_year == exp_data.end_year) &
                    (db.Experience.user == user_id)
                )
            )

            if exp:
                for point in exp_data.bullet_points:
                    if point and point.strip():
                        existing_bullet = await fetch_one(
                            db.ExperienceBullet.select().where(
                                (db.ExperienceBullet.text == point) &
                                (db.ExperienceBullet.experience == exp["id"])
                            )
                        )
                        if not existing_bullet:
                            await db.ExperienceBullet.insert(
                                db.ExperienceBullet(text=point, experience=exp["id"])
                            ).run()

    for proj_data in data.projects:
        if proj_data.project_name and proj_data.project_name.strip():
            existing_proj = await fetch_one(
                db.Project.select().where(
                    (db.Project.project_name == proj_data.project_name) &
                    (db.Project.github_link == proj_data.github_link) &
                    (db.Project.user == user_id)
                )
            )
            if not existing_proj:
                await db.Project.insert(
                    db.Project(
                        project_name=proj_data.project_name,
                        github_link=proj_data.github_link,
                        user=user_id
                    )
                ).run()

            proj = await fetch_one(
                db.Project.select().where(
                    (db.Project.project_name == proj_data.project_name) &
                    (db.Project.github_link == proj_data.github_link) &
                    (db.Project.user == user_id)
                )
            )

            if proj:
                for point in proj_data.bullet_points:
                    if point and point.strip():
                        existing_bullet = await fetch_one(
                            db.ProjectBullet.select().where(
                                (db.ProjectBullet.text == point) &
                                (db.ProjectBullet.project == proj["id"])
                            )
                        )
                        if not existing_bullet:
                            await db.ProjectBullet.insert(
                                db.ProjectBullet(text=point, project=proj["id"])
                            ).run()

    for edu_data in data.education:
        if edu_data.education_name and edu_data.education_name.strip():
            existing_edu = await fetch_one(
                db.Education.select().where(
                    (db.Education.education_name == edu_data.education_name) &
                    (db.Education.institution == edu_data.institution) &
                    (db.Education.start == edu_data.start) &
                    (db.Education.end == edu_data.end) &
                    (db.Education.grade == edu_data.grade) &
                    (db.Education.user == user_id)
                )
            )
            if not existing_edu:
                await db.Education.insert(
                    db.Education(
                        education_name=edu_data.education_name,
                        institution=edu_data.institution,
                        start=edu_data.start,
                        end=edu_data.end,
                        grade=edu_data.grade,
                        user=user_id
                    )
                ).run()

    for ref_data in data.references:
        if ref_data.referer_name and ref_data.referer_name.strip():
            existing_ref = await fetch_one(
                db.Reference.select().where(
                    (db.Reference.referer_name == ref_data.referer_name) &
                    (db.Reference.referer_institute == ref_data.referer_institute) &
                    (db.Reference.position == ref_data.position) &
                    (db.Reference.connection_type == ref_data.connection_type) &
                    (db.Reference.institution_url == ref_data.institution_url) &
                    (db.Reference.user == user_id)
                )
            )
            if not existing_ref:
                await db.Reference.insert(
                    db.Reference(
                        referer_name=ref_data.referer_name,
                        referer_institute=ref_data.referer_institute,
                        position=ref_data.position,
                        connection_type=ref_data.connection_type,
                        institution_url=ref_data.institution_url,
                        user=user_id
                    )
                ).run()

@app.post("/api/register")
async def register_user(user_data: UserCreate):
    existing = await fetch_one(
        db.User.select().where(db.User.email == user_data.email)
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    await db.User.insert(
        db.User(
            name=user_data.name,
            email=user_data.email,
            password_hash=hashed_password,
            phone=user_data.phone,
            location=user_data.location,
            linkedin=user_data.linkedin,
            github=user_data.github,
            website=user_data.website
        )
    ).run()

    return {"message": "User registered successfully"}


@app.post("/api/login")
async def login(user_data: UserLogin):
    user = await authenticate_user(user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )

    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False
    )
    return response


@app.get("/api/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response


@app.get("/templates")
async def list_templates():
    try:
        templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".typ")]
        return JSONResponse(templates)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/api/ats-gaps")
async def ats_gaps(
    payload: ATSOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    gaps = await run_ats_gaps(payload.job_description, user["id"])
    return gaps

@app.post("/api/ats-optimize")
async def ats_optimize(
    payload: ATSOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    ats_data = await run_ats_optimization(
        payload.job_description,
        user["id"],
        selected_missing_skills=payload.selected_missing_skills
    )
    return ats_data

@app.post("/api/ats-optimize")
async def ats_optimize(
    payload: ATSOptimizeRequest,
    user: dict = Depends(get_current_user)
):
    ats_data = await run_ats_optimization(payload.job_description, user["id"])
    return ats_data


@app.post("/generate-pdf")
async def generate_pdf(
    data: ResumeData,
    request: Request,
    user: dict = Depends(get_current_user)
):
    try:
        if data.job_description and app.state.azure_client:
            ats_data = await run_ats_optimization(data.job_description, user["id"])
            data.summary = ats_data.summary
            data.skills = ats_data.skills
            data.experience = ats_data.experience
            data.projects = ats_data.projects

        await save_resume_data(data, user["id"])

        template_name = request.headers.get("X-Template-Name", "resume.typ")
        template_path = os.path.join(TEMPLATE_DIR, template_name)

        if not os.path.exists(template_path):
            return JSONResponse({"error": f"Template '{template_name}' not found."}, status_code=404)

        env = jinja2.Environment(
            variable_start_string='{{',
            variable_end_string='}}',
            block_start_string='{%',
            block_end_string='%}',
            comment_start_string='{#JINJA#',
            comment_end_string='#JINJA#}'
        )
        env.filters['typst'] = py_to_typst
        with open(template_path) as f:
            typst_template = f.read()
        template = env.from_string(typst_template)

        with NamedTemporaryFile("w", suffix=".typ", delete=False) as typ_file:
            typ_file_path = typ_file.name

        # Copy icon files to the same directory as the .typ file
        typ_dir = os.path.dirname(typ_file_path)
        icon_files = ["email.png", "phone.png", "linkedin.png", "github.png", "location.png"]

        for icon_file in icon_files:
            source_path = os.path.join("static", icon_file)
            dest_path = os.path.join(typ_dir, icon_file)
            if os.path.exists(source_path):
                shutil.copy2(source_path, dest_path)

        image_typst_path = None
        image_full_path = None

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

                image_filename = "resume_image.png"
                image_full_path = os.path.join(typ_dir, image_filename)

                image.save(image_full_path, 'PNG', optimize=True)

                image_typst_path = image_filename

            except Exception as e:
                print(f"Error processing image: {e}")

        # Update contact info from user data
        contact_data = {
            "email": data.contact.email or user["email"],
            "phone": data.contact.phone or user["phone"],
            "location": data.contact.location or user["location"],
            "linkedin": data.contact.linkedin or user["linkedin"],
            "github": data.contact.github or user["github"],
            "website": data.contact.website or user["website"]
        }

        sanitized_exp : List[Experience] = []
        sanitized_edu : List[Education] = []

        for exp in data.experience:
            if exp.end_year == "":
                print("DHORA PORSE")
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
                print("DHORA PORSE")
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


        print("SANITIZED EXPERIENCE:")
        print(data.experience)
        print("SANITIZED EDUCATION:")
        print(data.education)

        typst_filled = template.render(
            name=data.name or user["name"],
            contact=py_to_typst(contact_data),
            summary=py_to_typst(data.summary),
            image_path=py_to_typst(image_typst_path),
            skills=py_to_typst([s.dict() for s in data.skills]),
            experience=py_to_typst([e.dict() for e in data.experience]),
            projects=py_to_typst([p.dict() for p in data.projects]),
            education=py_to_typst([e.dict() for e in data.education]),
            references=py_to_typst([r.dict() for r in data.references])
        )

        with open(typ_file_path, "w") as typ_file:
            typ_file.write(typst_filled)

        pdf_path = typ_file_path.replace(".typ", ".pdf")
        try:
            subprocess.run(["typst", "compile", typ_file_path, pdf_path], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("TYPST ERROR OUTPUT:", e.stderr)
            if image_full_path and os.path.exists(image_full_path):
                os.unlink(image_full_path)
            for icon_file in icon_files:
                icon_path_to_remove = os.path.join(typ_dir, icon_file)
                if os.path.exists(icon_path_to_remove):
                    os.unlink(icon_path_to_remove)
            return JSONResponse({"error": e.stderr}, status_code=500)

        # Clean up temp files after successful compilation
        if image_full_path and os.path.exists(image_full_path):
            os.unlink(image_full_path)

        for icon_file in icon_files:
            icon_path = os.path.join(typ_dir, icon_file)
            if os.path.exists(icon_path):
                os.unlink(icon_path)

        return FileResponse(pdf_path, media_type="application/pdf", filename="resume.pdf")
    except Exception as e:
        import traceback
        print("SERVER ERROR:", traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/save-json")
async def save_json(
    data: ResumeData,
    user: dict = Depends(get_current_user)
):
    await save_resume_data(data, user["id"])
    response_data = data.dict()
    response_data["image_base64"] = None if data.image_base64 else None
    return JSONResponse(response_data)


@app.get("/api/user-profile")
async def get_user_profile(user: dict = Depends(get_current_user)):
    return {
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"],
        "location": user["location"],
        "linkedin": user["linkedin"],
        "github": user["github"],
        "website": user["website"]
    }


@app.put("/api/user-profile")
async def update_user_profile(
    user_data: UserCreate,
    user: dict = Depends(get_current_user)
):
    await db.User.update({
        db.User.name: user_data.name,
        db.User.email: user_data.email,
        db.User.phone: user_data.phone,
        db.User.location: user_data.location,
        db.User.linkedin: user_data.linkedin,
        db.User.github: user_data.github,
        db.User.website: user_data.website,
        db.User.password_hash: get_password_hash(user_data.password) if user_data.password else user["password_hash"]
    }).where(db.User.id == user["id"]).run()

    updated = await fetch_one(db.User.select().where(db.User.id == user["id"]))
    return {
        "name": updated["name"],
        "email": updated["email"],
        "phone": updated["phone"],
        "location": updated["location"],
        "linkedin": updated["linkedin"],
        "github": updated["github"],
        "website": updated["website"]
    }


@app.get("/manage/personal-info", response_class=HTMLResponse)
async def manage_personal_info_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_personal_info.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/summaries")
async def get_summaries(q: Optional[str] = None, user: dict = Depends(get_current_user)):
    query = db.Summary.select(db.Summary.text).where(db.Summary.user == user["id"])
    if q:
        query = query.where(db.Summary.text.ilike(f"%{q}%"))
    summaries = await query.run()
    return [s["text"] for s in summaries]


@app.get("/api/summaries_with_ids")
async def get_summaries_with_ids(user: dict = Depends(get_current_user)):
    summaries = await db.Summary.select().where(db.Summary.user == user["id"]).order_by(db.Summary.id, ascending=False).run()
    return [{"id": s["id"], "text": s["text"]} for s in summaries]


@app.post("/api/summaries", status_code=status.HTTP_201_CREATED)
async def create_summary(
    summary_data: SummaryModel,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Summary.select().where(
            (db.Summary.text == summary_data.text) &
            (db.Summary.user == user["id"])
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Summary already exists.")

    inserted = await db.Summary.insert(
        db.Summary(text=summary_data.text, user=user["id"])
    ).returning(db.Summary.id).run()
    summary_id = inserted[0]["id"]
    return {"id": summary_id, "text": summary_data.text}


@app.put("/api/summaries/{summary_id}")
async def update_summary(
    summary_id: int,
    summary_data: SummaryModel,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Summary.select().where(
            (db.Summary.id == summary_id) & (db.Summary.user == user["id"])
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Summary not found")

    await db.Summary.update({
        db.Summary.text: summary_data.text
    }).where(db.Summary.id == summary_id).run()

    return {"id": summary_id, "text": summary_data.text}


@app.delete("/api/summaries/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_summary(
    summary_id: int,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Summary.select().where(
            (db.Summary.id == summary_id) & (db.Summary.user == user["id"])
        )
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Summary not found")

    await db.Summary.delete().where(db.Summary.id == summary_id).run()
    return


@app.get("/manage/summaries", response_class=HTMLResponse)
async def manage_summaries_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_summaries.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/skills")
async def get_skills(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = db.Skill.select().where(db.Skill.user == user["id"])
    if q:
        query = query.where(db.Skill.skill_name.ilike(f"%{q}%"))
    skills = await query.order_by(db.Skill.id, ascending=False).run()

    results = []
    for s in skills:
        bullets = await db.SkillBullet.select(db.SkillBullet.text).where(db.SkillBullet.skill == s["id"]).run()
        results.append({
            "id": s["id"],
            "skill_name": s["skill_name"],
            "bullet_points": [b["text"] for b in bullets]
        })
    return results


@app.get("/api/skills_with_bullets")
async def get_skills_with_bullets(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    return await get_skills(q=q, user=user)


@app.get("/api/skills/{skill_id}/bullets")
async def get_skill_bullets(
    skill_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    skill = await fetch_one(
        db.Skill.select().where(
            (db.Skill.id == skill_id) & (db.Skill.user == user["id"])
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    query = db.SkillBullet.select(db.SkillBullet.text).where(db.SkillBullet.skill == skill_id)
    if q:
        query = query.where(db.SkillBullet.text.ilike(f"%{q}%"))
    bullets = await query.run()
    return [b["text"] for b in bullets]


@app.post("/api/skills", status_code=status.HTTP_201_CREATED)
async def create_skill(
    skill_data: Skill,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Skill.select().where(
            (db.Skill.user == user["id"]) & (db.Skill.skill_name == skill_data.skill_name)
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="A skill with this name already exists.")

    inserted = await db.Skill.insert(
        db.Skill(skill_name=skill_data.skill_name, user=user["id"])
    ).returning(db.Skill.id).run()
    skill_id = inserted[0]["id"]

    for point in skill_data.bullet_points:
        await db.SkillBullet.insert(
            db.SkillBullet(text=point, skill=skill_id)
        ).run()

    bullets = await db.SkillBullet.select(db.SkillBullet.text).where(db.SkillBullet.skill == skill_id).run()
    return {
        "id": skill_id,
        "skill_name": skill_data.skill_name,
        "bullet_points": [b["text"] for b in bullets]
    }


@app.put("/api/skills/{skill_id}")
async def update_skill(
    skill_id: int,
    skill_data: Skill,
    user: dict = Depends(get_current_user)
):
    skill = await fetch_one(
        db.Skill.select().where(
            (db.Skill.id == skill_id) & (db.Skill.user == user["id"])
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    await db.Skill.update({
        db.Skill.skill_name: skill_data.skill_name
    }).where(db.Skill.id == skill_id).run()

    await db.SkillBullet.delete().where(db.SkillBullet.skill == skill_id).run()
    for point in skill_data.bullet_points:
        await db.SkillBullet.insert(
            db.SkillBullet(text=point, skill=skill_id)
        ).run()

    bullets = await db.SkillBullet.select(db.SkillBullet.text).where(db.SkillBullet.skill == skill_id).run()
    return {
        "id": skill_id,
        "skill_name": skill_data.skill_name,
        "bullet_points": [b["text"] for b in bullets]
    }


@app.delete("/api/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: int,
    user: dict = Depends(get_current_user)
):
    skill = await fetch_one(
        db.Skill.select().where(
            (db.Skill.id == skill_id) & (db.Skill.user == user["id"])
        )
    )
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    await db.Skill.delete().where(db.Skill.id == skill_id).run()
    return


@app.get("/manage/skills", response_class=HTMLResponse)
async def manage_skills_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_skills.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/projects")
async def get_projects(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = db.Project.select().where(db.Project.user == user["id"])
    if q:
        query = query.where(db.Project.project_name.ilike(f"%{q}%"))
    projects = await query.run()

    results = []
    for p in projects:
        bullets = await db.ProjectBullet.select(db.ProjectBullet.text).where(db.ProjectBullet.project == p["id"]).run()
        results.append({
            "id": p["id"],
            "project_name": p["project_name"],
            "github_link": p["github_link"],
            "bullet_points": [b["text"] for b in bullets]
        })
    return results


@app.get("/api/projects/{project_id}/bullets")
async def get_project_bullets(
    project_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    project = await fetch_one(
        db.Project.select().where(
            (db.Project.id == project_id) & (db.Project.user == user["id"])
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = db.ProjectBullet.select(db.ProjectBullet.text).where(db.ProjectBullet.project == project_id)
    if q:
        query = query.where(db.ProjectBullet.text.ilike(f"%{q}%"))
    bullets = await query.run()
    return [b["text"] for b in bullets]



@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: Project,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Project.select().where(
            (db.Project.project_name == project_data.project_name) &
            (db.Project.github_link == project_data.github_link) &
            (db.Project.user == user["id"])
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Project already exists.")

    inserted = await db.Project.insert(
        db.Project(
            project_name=project_data.project_name,
            github_link=project_data.github_link,
            user=user["id"]
        )
    ).returning(db.Project.id).run()
    project_id = inserted[0]["id"]

    for point in project_data.bullet_points:
        await db.ProjectBullet.insert(
            db.ProjectBullet(text=point, project=project_id)
        ).run()

    bullets = await db.ProjectBullet.select(db.ProjectBullet.text).where(db.ProjectBullet.project == project_id).run()
    return {
        "id": project_id,
        "project_name": project_data.project_name,
        "github_link": project_data.github_link,
        "bullet_points": [b["text"] for b in bullets]
    }

@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: int,
    project_data: Project,
    user: dict = Depends(get_current_user)
):
    project = await fetch_one(
        db.Project.select().where(
            (db.Project.id == project_id) & (db.Project.user == user["id"])
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.Project.update({
        db.Project.project_name: project_data.project_name,
        db.Project.github_link: project_data.github_link
    }).where(db.Project.id == project_id).run()

    await db.ProjectBullet.delete().where(db.ProjectBullet.project == project_id).run()
    for point in project_data.bullet_points:
        await db.ProjectBullet.insert(
            db.ProjectBullet(text=point, project=project_id)
        ).run()

    bullets = await db.ProjectBullet.select(db.ProjectBullet.text).where(db.ProjectBullet.project == project_id).run()
    return {
        "id": project_id,
        "project_name": project_data.project_name,
        "github_link": project_data.github_link,
        "bullet_points": [b["text"] for b in bullets]
    }


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    user: dict = Depends(get_current_user)
):
    project = await fetch_one(
        db.Project.select().where(
            (db.Project.id == project_id) & (db.Project.user == user["id"])
        )
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.Project.delete().where(db.Project.id == project_id).run()
    return


@app.get("/manage/projects", response_class=HTMLResponse)
async def manage_projects_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_projects.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/experiences")
async def get_experiences(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = db.Experience.select().where(db.Experience.user == user["id"])
    if q:
        query = query.where(db.Experience.experience_name.ilike(f"%{q}%"))
    exps = await query.run()

    results = []
    for e in exps:
        bullets = await db.ExperienceBullet.select(db.ExperienceBullet.text).where(db.ExperienceBullet.experience == e["id"]).run()
        results.append({
            "id": e["id"],
            "experience_name": e["experience_name"],
            "start_year": e["start_year"],
            "end_year": e["end_year"],
            "bullet_points": [b["text"] for b in bullets]
        })
    return results


@app.get("/api/experiences/{experience_id}/bullets")
async def get_experience_bullets(
    experience_id: int,
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    exp = await fetch_one(
        db.Experience.select().where(
            (db.Experience.id == experience_id) & (db.Experience.user == user["id"])
        )
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    query = db.ExperienceBullet.select(db.ExperienceBullet.text).where(db.ExperienceBullet.experience == experience_id)
    if q:
        query = query.where(db.ExperienceBullet.text.ilike(f"%{q}%"))
    bullets = await query.run()
    return [b["text"] for b in bullets]


@app.post("/api/experiences", status_code=status.HTTP_201_CREATED)
async def create_experience(
    exp_data: Experience,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Experience.select().where(
            (db.Experience.experience_name == exp_data.experience_name) &
            (db.Experience.start_year == exp_data.start_year) &
            (db.Experience.end_year == exp_data.end_year) &
            (db.Experience.user == user["id"])
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Experience already exists.")

    inserted = await db.Experience.insert(
        db.Experience(
            experience_name=exp_data.experience_name,
            start_year=exp_data.start_year,
            end_year=exp_data.end_year,
            user=user["id"]
        )
    ).returning(db.Experience.id).run()
    exp_id = inserted[0]["id"]

    for point in exp_data.bullet_points:
        await db.ExperienceBullet.insert(
            db.ExperienceBullet(text=point, experience=exp_id)
        ).run()

    bullets = await db.ExperienceBullet.select(db.ExperienceBullet.text).where(db.ExperienceBullet.experience == exp_id).run()
    return {
        "id": exp_id,
        "experience_name": exp_data.experience_name,
        "start_year": exp_data.start_year,
        "end_year": exp_data.end_year,
        "bullet_points": [b["text"] for b in bullets]
    }

@app.put("/api/experiences/{experience_id}")
async def update_experience(
    experience_id: int,
    exp_data: Experience,
    user: dict = Depends(get_current_user)
):
    exp = await fetch_one(
        db.Experience.select().where(
            (db.Experience.id == experience_id) & (db.Experience.user == user["id"])
        )
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    await db.Experience.update({
        db.Experience.experience_name: exp_data.experience_name,
        db.Experience.start_year: exp_data.start_year,
        db.Experience.end_year: exp_data.end_year,
    }).where(db.Experience.id == experience_id).run()

    await db.ExperienceBullet.delete().where(db.ExperienceBullet.experience == experience_id).run()
    for point in exp_data.bullet_points:
        await db.ExperienceBullet.insert(
            db.ExperienceBullet(text=point, experience=experience_id)
        ).run()

    bullets = await db.ExperienceBullet.select(db.ExperienceBullet.text).where(db.ExperienceBullet.experience == experience_id).run()
    return {
        "id": experience_id,
        "experience_name": exp_data.experience_name,
        "start_year": exp_data.start_year,
        "end_year": exp_data.end_year,
        "bullet_points": [b["text"] for b in bullets]
    }


@app.delete("/api/experiences/{experience_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    experience_id: int,
    user: dict = Depends(get_current_user)
):
    exp = await fetch_one(
        db.Experience.select().where(
            (db.Experience.id == experience_id) & (db.Experience.user == user["id"])
        )
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    await db.Experience.delete().where(db.Experience.id == experience_id).run()
    return


@app.get("/manage/experience", response_class=HTMLResponse)
async def manage_experience_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_experience.html") as f:
        return HTMLResponse(f.read())


@app.get("/api/educations")
async def get_educations(
    q: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = db.Education.select().where(db.Education.user == user["id"])
    if q:
        query = query.where(
            (db.Education.education_name.ilike(f"%{q}%")) |
            (db.Education.institution.ilike(f"%{q}%"))
        )
    edus = await query.run()
    return edus



@app.post("/api/educations", status_code=status.HTTP_201_CREATED)
async def create_education(
    edu_data: Education,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Education.select().where(
            (db.Education.education_name == edu_data.education_name) &
            (db.Education.institution == edu_data.institution) &
            (db.Education.start == edu_data.start) &
            (db.Education.end == edu_data.end) &
            (db.Education.grade == edu_data.grade) &
            (db.Education.user == user["id"])
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Education already exists.")

    inserted = await db.Education.insert(
        db.Education(
            education_name=edu_data.education_name,
            institution=edu_data.institution,
            start=edu_data.start,
            end=edu_data.end,
            grade=edu_data.grade,
            user=user["id"]
        )
    ).returning(db.Education.id).run()
    edu_id = inserted[0]["id"]
    edu = await fetch_one(db.Education.select().where(db.Education.id == edu_id))
    return edu


@app.put("/api/educations/{education_id}")
async def update_education(
    education_id: int,
    edu_data: Education,
    user: dict = Depends(get_current_user)
):
    edu = await fetch_one(
        db.Education.select().where(
            (db.Education.id == education_id) & (db.Education.user == user["id"])
        )
    )
    if not edu:
        raise HTTPException(status_code=404, detail="Education not found")

    await db.Education.update({
        db.Education.education_name: edu_data.education_name,
        db.Education.institution: edu_data.institution,
        db.Education.start: edu_data.start,
        db.Education.end: edu_data.end,
        db.Education.grade: edu_data.grade
    }).where(db.Education.id == education_id).run()

    updated = await fetch_one(db.Education.select().where(db.Education.id == education_id))
    return updated


@app.delete("/api/educations/{education_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(
    education_id: int,
    user: dict = Depends(get_current_user)
):
    edu = await fetch_one(
        db.Education.select().where(
            (db.Education.id == education_id) & (db.Education.user == user["id"])
        )
    )
    if not edu:
        raise HTTPException(status_code=404, detail="Education not found")

    await db.Education.delete().where(db.Education.id == education_id).run()
    return


@app.get("/manage/education", response_class=HTMLResponse)
async def manage_education_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_education.html") as f:
        return HTMLResponse(f.read())



@app.post("/api/references", status_code=status.HTTP_201_CREATED)
async def create_reference(
    ref_data: Reference,
    user: dict = Depends(get_current_user)
):
    existing = await fetch_one(
        db.Reference.select().where(
            (db.Reference.referer_name == ref_data.referer_name) &
            (db.Reference.referer_institute == ref_data.referer_institute) &
            (db.Reference.position == ref_data.position) &
            (db.Reference.connection_type == ref_data.connection_type) &
            (db.Reference.institution_url == ref_data.institution_url) &
            (db.Reference.user == user["id"])
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Reference already exists.")

    inserted = await db.Reference.insert(
        db.Reference(
            referer_name=ref_data.referer_name,
            referer_institute=ref_data.referer_institute,
            position=ref_data.position,
            connection_type=ref_data.connection_type,
            institution_url=ref_data.institution_url,
            user=user["id"]
        )
    ).returning(db.Reference.id).run()
    ref_id = inserted[0]["id"]
    ref = await fetch_one(db.Reference.select().where(db.Reference.id == ref_id))
    return ref


@app.put("/api/references/{reference_id}")
async def update_reference(
    reference_id: int,
    ref_data: Reference,
    user: dict = Depends(get_current_user)
):
    ref = await fetch_one(
        db.Reference.select().where(
            (db.Reference.id == reference_id) & (db.Reference.user == user["id"])
        )
    )
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")

    await db.Reference.update({
        db.Reference.referer_name: ref_data.referer_name,
        db.Reference.referer_institute: ref_data.referer_institute,
        db.Reference.position: ref_data.position,
        db.Reference.connection_type: ref_data.connection_type,
        db.Reference.institution_url: ref_data.institution_url
    }).where(db.Reference.id == reference_id).run()

    updated = await fetch_one(db.Reference.select().where(db.Reference.id == reference_id))
    return updated


@app.delete("/api/references/{reference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reference(
    reference_id: int,
    user: dict = Depends(get_current_user)
):
    ref = await fetch_one(
        db.Reference.select().where(
            (db.Reference.id == reference_id) & (db.Reference.user == user["id"])
        )
    )
    if not ref:
        raise HTTPException(status_code=404, detail="Reference not found")

    await db.Reference.delete().where(db.Reference.id == reference_id).run()
    return


@app.get("/manage/references", response_class=HTMLResponse)
async def manage_references_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/manage_references.html") as f:
        return HTMLResponse(f.read())


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    with open("frontend/register.html") as f:
        return HTMLResponse(f.read())


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("frontend/login.html") as f:
        return HTMLResponse(f.read())


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/login", status_code=303)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.utcfromtimestamp(payload.get("exp")) < datetime.utcnow():
            response = RedirectResponse(url="/login", status_code=303)
            response.delete_cookie(key="access_token")
            return response
    except JWTError:
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="access_token")
        return response

    with open("frontend/dashboard.html") as f:
        return HTMLResponse(f.read())


@app.get("/generate", response_class=HTMLResponse)
async def generate_page(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        return RedirectResponse(url="/login", status_code=303)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.utcfromtimestamp(payload.get("exp")) < datetime.utcnow():
            return RedirectResponse(url="/login", status_code=303)
    except JWTError:
        return RedirectResponse(url="/login", status_code=303)

    with open("frontend/generate.html") as f:
        return HTMLResponse(f.read())


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=404)