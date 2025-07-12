from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Depends, HTTPException, status, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from tempfile import NamedTemporaryFile
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from PIL import Image
import os
import shutil
import jinja2
import base64
import io
import subprocess
import traceback
from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import database as db
from sqlalchemy import or_
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

db.create_db_and_tables()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

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

class Skill(BaseModel):
    skill_name: str
    bullet_points: List[str]

class Experience(BaseModel):
    experience_name: str
    bullet_points: List[str]
    start_year: Optional[str] = None
    end_year: Optional[str] = None
    ongoing: Optional[bool] = False

class Project(BaseModel):
    project_name: str
    bullet_points: List[str]
    github_link: Optional[str] = None

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

# Authentication functions
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

def authenticate_user(db_session, email: str, password: str):
    user = db_session.query(db.User).filter(db.User.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

async def get_current_user(request: Request, db_session: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        # Try to get token from Authorization header
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
        token_data = TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = db_session.query(db.User).filter(db.User.id == user_id).first()
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

def save_resume_data(data: ResumeData, db_session: Session, user_id: int):
    # Save summary
    if data.summary and data.summary.strip():
        stmt = sqlite_insert(db.Summary).values(text=data.summary, user_id=user_id).on_conflict_do_nothing()
        db_session.execute(stmt)

    # Save skills and bullets
    for skill_data in data.skills:
        if skill_data.skill_name and skill_data.skill_name.strip():
            # Insert skill
            skill_stmt = sqlite_insert(db.Skill).values(
                skill_name=skill_data.skill_name,
                user_id=user_id
            ).on_conflict_do_nothing()
            db_session.execute(skill_stmt)
            db_session.commit()
            
            skill = db_session.query(db.Skill).filter_by(
                skill_name=skill_data.skill_name,
                user_id=user_id
            ).first()

            if skill:
                for point in skill_data.bullet_points:
                    if point and point.strip():
                        bullet_stmt = sqlite_insert(db.SkillBullet).values(
                            text=point, 
                            skill_id=skill.id
                        ).on_conflict_do_nothing()
                        db_session.execute(bullet_stmt)

    # Save experiences and bullets
    for exp_data in data.experience:
        if exp_data.experience_name and exp_data.experience_name.strip():
            exp_values = exp_data.dict(exclude={'bullet_points'})
            exp_values['user_id'] = user_id
            exp_stmt = sqlite_insert(db.Experience).values(**exp_values).on_conflict_do_nothing()
            db_session.execute(exp_stmt)
            db_session.commit()

            exp = db_session.query(db.Experience).filter_by(
                experience_name=exp_data.experience_name, 
                start_year=exp_data.start_year, 
                end_year=exp_data.end_year, 
                ongoing=exp_data.ongoing,
                user_id=user_id
            ).first()
            
            if exp:
                for point in exp_data.bullet_points:
                    if point and point.strip():
                        bullet_stmt = sqlite_insert(db.ExperienceBullet).values(
                            text=point, 
                            experience_id=exp.id
                        ).on_conflict_do_nothing()
                        db_session.execute(bullet_stmt)

    # Save projects and bullets
    for proj_data in data.projects:
        if proj_data.project_name and proj_data.project_name.strip():
            proj_values = proj_data.dict(exclude={'bullet_points'})
            proj_values['user_id'] = user_id
            proj_stmt = sqlite_insert(db.Project).values(**proj_values).on_conflict_do_nothing()
            db_session.execute(proj_stmt)
            db_session.commit()

            proj = db_session.query(db.Project).filter_by(
                project_name=proj_data.project_name, 
                github_link=proj_data.github_link,
                user_id=user_id
            ).first()
            
            if proj:
                for point in proj_data.bullet_points:
                    if point and point.strip():
                        bullet_stmt = sqlite_insert(db.ProjectBullet).values(
                            text=point, 
                            project_id=proj.id
                        ).on_conflict_do_nothing()
                        db_session.execute(bullet_stmt)

    # Save education
    for edu_data in data.education:
        if edu_data.education_name and edu_data.education_name.strip():
            edu_values = edu_data.dict()
            edu_values['user_id'] = user_id
            edu_stmt = sqlite_insert(db.Education).values(**edu_values).on_conflict_do_nothing()
            db_session.execute(edu_stmt)

    # Save references
    for ref_data in data.references:
        if ref_data.referer_name and ref_data.referer_name.strip():
            ref_values = ref_data.dict()
            ref_values['user_id'] = user_id
            ref_stmt = sqlite_insert(db.Reference).values(**ref_values).on_conflict_do_nothing()
            db_session.execute(ref_stmt)

    db_session.commit()

# User registration and login endpoints
@app.post("/api/register")
async def register_user(user_data: UserCreate, db_session: Session = Depends(get_db)):
    db_user = db_session.query(db.User).filter(db.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    db_user = db.User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        phone=user_data.phone,
        location=user_data.location,
        linkedin=user_data.linkedin,
        github=user_data.github,
        website=user_data.website
    )
    
    db_session.add(db_user)
    db_session.commit()
    db_session.refresh(db_user)
    
    return {"message": "User registered successfully"}

@app.post("/api/login")
async def login(user_data: UserLogin, db_session: Session = Depends(get_db)):
    user = authenticate_user(db_session, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    response = JSONResponse({"access_token": access_token, "token_type": "bearer"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
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

@app.post("/generate-pdf")
async def generate_pdf(
    data: ResumeData, 
    request: Request, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    try:
        save_resume_data(data, db_session, user.id)

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
            "email": data.contact.email or user.email,
            "phone": data.contact.phone or user.phone,
            "location": data.contact.location or user.location,
            "linkedin": data.contact.linkedin or user.linkedin,
            "github": data.contact.github or user.github,
            "website": data.contact.website or user.website
        }

        typst_filled = template.render(
            name=data.name or user.name,
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
            # Clean up temp files on error
            if image_full_path and os.path.exists(image_full_path):
                os.unlink(image_full_path)
            # Clean up icon files
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
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    save_resume_data(data, db_session, user.id)
    response_data = data.dict()
    response_data["image_base64"] = None if data.image_base64 else None
    return JSONResponse(response_data)

@app.get("/api/user-profile")
async def get_user_profile(user: db.User = Depends(get_current_user)):
    return {
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "location": user.location,
        "linkedin": user.linkedin,
        "github": user.github,
        "website": user.website
    }

@app.get("/api/summaries")
async def get_summaries(q: Optional[str] = None, user: db.User = Depends(get_current_user), db_session: Session = Depends(get_db)):
    query = db_session.query(db.Summary.text).filter(db.Summary.user_id == user.id)
    if q:
        query = query.filter(db.Summary.text.ilike(f"%{q}%"))
    summaries = query.all()
    return [s[0] for s in summaries]

@app.get("/api/skills/{skill_id}/bullets")
async def get_skill_bullets(
    skill_id: int, 
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    # Verify the skill belongs to the user
    skill = db_session.query(db.Skill).filter(
        db.Skill.id == skill_id,
        db.Skill.user_id == user.id
    ).first()
    
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    query = db_session.query(db.SkillBullet.text).filter(db.SkillBullet.skill_id == skill_id)
    if q:
        query = query.filter(db.SkillBullet.text.ilike(f"%{q}%"))
    bullets = query.distinct().all()
    return [b[0] for b in bullets]

@app.get("/api/experiences/{experience_id}/bullets")
async def get_experience_bullets(
    experience_id: int, 
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    # Verify the experience belongs to the user
    exp = db_session.query(db.Experience).filter(
        db.Experience.id == experience_id,
        db.Experience.user_id == user.id
    ).first()
    
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
        
    query = db_session.query(db.ExperienceBullet.text).filter(db.ExperienceBullet.experience_id == experience_id)
    if q:
        query = query.filter(db.ExperienceBullet.text.ilike(f"%{q}%"))
    bullets = query.distinct().all()
    return [b[0] for b in bullets]

@app.get("/api/projects/{project_id}/bullets")
async def get_project_bullets(
    project_id: int, 
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    # Verify the project belongs to the user
    project = db_session.query(db.Project).filter(
        db.Project.id == project_id,
        db.Project.user_id == user.id
    ).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    query = db_session.query(db.ProjectBullet.text).filter(db.ProjectBullet.project_id == project_id)
    if q:
        query = query.filter(db.ProjectBullet.text.ilike(f"%{q}%"))
    bullets = query.distinct().all()
    return [b[0] for b in bullets]

@app.get("/api/skills")
async def get_skills(
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    query = db_session.query(db.Skill).filter(db.Skill.user_id == user.id)
    if q:
        query = query.filter(db.Skill.skill_name.ilike(f"%{q}%"))
    skills = query.all()
    return [{"id": s.id, "skill_name": s.skill_name} for s in skills]

@app.get("/api/experiences")
async def get_experiences(
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    query = db_session.query(db.Experience).filter(db.Experience.user_id == user.id)
    if q:
        query = query.filter(db.Experience.experience_name.ilike(f"%{q}%"))
    exps = query.all()
    return [{
        "id": e.id,
        "experience_name": e.experience_name, 
        "start_year": e.start_year,
        "end_year": e.end_year,
        "ongoing": e.ongoing,
        "bullet_points": [b.text for b in e.bullet_points]
    } for e in exps]

@app.get("/api/projects")
async def get_projects(
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    query = db_session.query(db.Project).filter(db.Project.user_id == user.id)
    if q:
        query = query.filter(db.Project.project_name.ilike(f"%{q}%"))
    projects = query.all()
    return [{"id": p.id, "project_name": p.project_name, "github_link": p.github_link, "bullet_points": [b.text for b in p.bullet_points]} for p in projects]

@app.get("/api/educations")
async def get_educations(
    q: Optional[str] = None, 
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    query = db_session.query(db.Education).filter(db.Education.user_id == user.id)
    if q:
        query = query.filter(
            or_(
                db.Education.education_name.ilike(f"%{q}%"),
                db.Education.institution.ilike(f"%{q}%")
            )
        )
    edus = query.all()
    return edus

@app.get("/api/references")
async def get_references(
    user: db.User = Depends(get_current_user),
    db_session: Session = Depends(get_db)
):
    refs = db_session.query(db.Reference).filter(db.Reference.user_id == user.id).all()
    return refs

# Define routes for HTML pages
@app.get("/register", response_class=HTMLResponse)
async def register_page():
    with open("frontend/register.html") as f:
        return HTMLResponse(f.read())

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    with open("frontend/login.html") as f:
        return HTMLResponse(f.read())

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
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