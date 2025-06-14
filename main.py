from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from tempfile import NamedTemporaryFile
from typing import List, Optional
from pydantic import BaseModel
from PIL import Image
import os
import shutil
import jinja2
import base64
import io
import subprocess
import traceback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_DIR = "templates"

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
    years: Optional[str] = None

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

@app.get("/templates")
async def list_templates():
    try:
        templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".typ")]
        return JSONResponse(templates)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/generate-pdf")
async def generate_pdf(data: ResumeData, request: Request):
    try:
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
                    header, image_data_b64 = data.image_base64.split(',', 1)
                    image_data_b64 = data.image_base64.split(',', 1)[1] # Added to handle data URL prefix
                else:
                    image_data_b64 = data.image_base64
                
                image_data = base64.b64decode(image_data_b64)
                
                image = Image.open(io.BytesIO(image_data))
                
                if image.mode in ('RGBA', 'LA', 'P'):
                    image = image.convert('RGB') # Convert to RGB if has alpha or is palette-based
                elif image.mode != 'RGB':
                    image = image.convert('RGB') # Convert other modes to RGB
                
                image_filename = "resume_image.png"
                image_full_path = os.path.join(typ_dir, image_filename)
                
                image.save(image_full_path, 'PNG', optimize=True)
                
                image_typst_path = image_filename
                
            except Exception as e:
                print(f"Error processing image: {e}")

        typst_filled = template.render(
            name=data.name,
            contact=py_to_typst(data.contact.dict()),
            summary=py_to_typst(data.summary),
            image_path=py_to_typst(image_typst_path),
            skills=py_to_typst([s.dict() for s in data.skills]),
            experience=py_to_typst([e.dict() for e in data.experience]),
            projects=py_to_typst([p.dict() for p in data.projects]),
            education=py_to_typst([e.dict() for e in data.education]),
            references=py_to_typst([r.dict() for r in data.references])
        )
        print("---- FILLED TYPST TEMPLATE ----")
        print(typst_filled)
        print("-----------------------------")
        
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
                icon_path_to_remove = os.path.join(typ_dir, icon_file) # Corrected variable name
                if os.path.exists(icon_path_to_remove): # Check before unlinking
                    os.unlink(icon_path_to_remove)
            return JSONResponse({"error": e.stderr}, status_code=500)
        
        # Clean up temp files after successful compilation
        if image_full_path and os.path.exists(image_full_path):
            os.unlink(image_full_path)
        
        # Clean up icon files
        for icon_file in icon_files:
            icon_path = os.path.join(typ_dir, icon_file)
            if os.path.exists(icon_path):
                os.unlink(icon_path) # Unlink the copied icon files

        return FileResponse(pdf_path, media_type="application/pdf", filename="resume.pdf")
    except Exception as e:
        import traceback
        print("SERVER ERROR:", traceback.format_exc())
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/save-json")
async def save_json(data: ResumeData):
    return JSONResponse(data.dict())

@app.get("/")
async def index():
    with open("frontend.html") as f:
        return HTMLResponse(f.read())

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({}, status_code=404)
