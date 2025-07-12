from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Table, Boolean, UniqueConstraint, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# DATABASE_URL = "sqlite:///./resume.db"
DATABASE_URL = "sqlite:///./data/resume.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    website = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(Integer, primary_key=True, index=True)
    skill_name = Column(String, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bullet_points = relationship("SkillBullet", back_populates="skill", cascade="all, delete-orphan")
    user = relationship("User")
    __table_args__ = (UniqueConstraint('skill_name', 'user_id', name='_skill_user_uc'),)

class SkillBullet(Base):
    __tablename__ = "skill_bullets"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    skill_id = Column(Integer, ForeignKey("skills.id"))
    skill = relationship("Skill", back_populates="bullet_points")
    __table_args__ = (UniqueConstraint('text', 'skill_id', name='_text_skill_uc'),)

class Experience(Base):
    __tablename__ = "experiences"
    id = Column(Integer, primary_key=True, index=True)
    experience_name = Column(String, index=True)
    start_year = Column(String, nullable=True)
    end_year = Column(String, nullable=True)
    ongoing = Column(Boolean, default=False)
    bullet_points = relationship("ExperienceBullet", back_populates="experience", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    __table_args__ = (UniqueConstraint('experience_name', 'start_year', 'end_year', 'ongoing', 'user_id', name='_exp_uc'),)

class ExperienceBullet(Base):
    __tablename__ = "experience_bullets"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    experience_id = Column(Integer, ForeignKey("experiences.id"))
    experience = relationship("Experience", back_populates="bullet_points")
    __table_args__ = (UniqueConstraint('text', 'experience_id', name='_text_exp_uc'),)

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)
    github_link = Column(String, nullable=True)
    bullet_points = relationship("ProjectBullet", back_populates="project", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    __table_args__ = (UniqueConstraint('project_name', 'github_link', 'user_id', name='_proj_uc'),)

class ProjectBullet(Base):
    __tablename__ = "project_bullets"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project", back_populates="bullet_points")
    __table_args__ = (UniqueConstraint('text', 'project_id', name='_text_proj_uc'),)

class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True, index=True)
    education_name = Column(String)
    institution = Column(String)
    start = Column(String, nullable=True)
    end = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    __table_args__ = (UniqueConstraint('education_name', 'institution', 'start', 'end', 'grade', 'user_id', name='_edu_uc'),)

class Reference(Base):
    __tablename__ = "references"
    id = Column(Integer, primary_key=True, index=True)
    referer_name = Column(String)
    referer_institute = Column(String)
    position = Column(String, nullable=True)
    connection_type = Column(String, nullable=True)
    institution_url = Column(String, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    __table_args__ = (UniqueConstraint('referer_name', 'referer_institute', 'position', 'user_id', name='_ref_uc'),)

class Summary(Base):
    __tablename__ = "summaries"
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")
    __table_args__ = (UniqueConstraint('text', 'user_id', name='_summary_user_uc'),)

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)