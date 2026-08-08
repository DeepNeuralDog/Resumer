"""Pydantic models for request/response validation."""
from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# USER MODELS
# =============================================================================

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


# =============================================================================
# CONTACT MODEL
# =============================================================================

class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


# =============================================================================
# SUMMARY MODEL
# =============================================================================

class SummaryModel(BaseModel):
    text: str


# =============================================================================
# SKILL MODELS
# =============================================================================

class Skill(BaseModel):
    skill_name: str = Field(description="Name of the Skill Group/Category. This describes a category of skills which are related.")
    bullet_points: List[str] = Field(description="List of bullet points describing the skill category")

    def to_ai_context_string(self) -> str:
        bullets_str = "Skill_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Skill Catetory:  {self.skill_name}:\n{bullets_str}"


# =============================================================================
# EXPERIENCE MODELS
# =============================================================================

class Experience(BaseModel):
    experience_name: str = Field(description="Name of the Experience")
    bullet_points: List[str] = Field(description="List of bullet points describing the experience")
    start_year: Optional[str] = None
    end_year: Optional[str] = None

    def to_ai_context_string(self) -> str:
        bullets_str = "Experience_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Experience:  {self.experience_name} (From {self.start_year} to {self.end_year}):\n{bullets_str}"


# =============================================================================
# PROJECT MODELS
# =============================================================================

class Project(BaseModel):
    project_name: str = Field(description="Name of the Project")
    bullet_points: List[str] = Field(description="List of bullet points describing the project")
    github_link: Optional[str] = None

    def to_ai_context_string(self) -> str:
        bullets_str = "Project_Bullet_Points\n".join([f"- {bp}" for bp in self.bullet_points])
        return f"Project:  {self.project_name} (GitHub: {self.github_link}):\n{bullets_str}"


# =============================================================================
# EDUCATION MODELS
# =============================================================================

class Education(BaseModel):
    education_name: str
    institution: str
    start: Optional[str] = None
    end: Optional[str] = None
    grade: Optional[str] = None


# =============================================================================
# REFERENCE MODELS
# =============================================================================

class Reference(BaseModel):
    referer_name: str
    referer_institute: str
    position: Optional[str] = None
    connection_type: Optional[str] = None
    institution_url: Optional[str] = None


# =============================================================================
# RESUME DATA MODELS
# =============================================================================

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


# =============================================================================
# ATS MODELS
# =============================================================================

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
