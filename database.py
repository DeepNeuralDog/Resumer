from piccolo.engine.sqlite import SQLiteEngine
from piccolo.table import Table, create_tables
from piccolo.columns import (
    Serial, Varchar, Text, Boolean, ForeignKey, Timestamptz
)
from dotenv import load_dotenv
import os
import datetime
from pathlib import Path

load_dotenv()

# SQLite database file in workspace
DB_PATH = os.getenv("SQLITE_DB_PATH", str(Path(__file__).parent / "resumer.db"))

engine = SQLiteEngine(path=DB_PATH)



class User(Table, db=engine, tablename="users"):
    id = Serial(primary_key=True)
    name = Varchar(length=255, null=False)
    email = Varchar(length=255, null=False, unique=True)
    password_hash = Varchar(length=255, null=False)
    phone = Varchar(length=50, null=True)
    location = Varchar(length=255, null=True)
    linkedin = Varchar(length=255, null=True)
    github = Varchar(length=255, null=True)
    website = Varchar(length=255, null=True)
    created_at = Timestamptz(default=datetime.datetime.now)


class Skill(Table, db=engine, tablename="skills"):
    id = Serial(primary_key=True)
    skill_name = Varchar(length=255, null=False)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("skill_name", "user")]


class SkillBullet(Table, db=engine, tablename="skill_bullets"):
    id = Serial(primary_key=True)
    text = Varchar(length=1024, null=False)
    skill = ForeignKey(Skill)

    class Meta:
        unique_together = [("text", "skill")]


class Experience(Table, db=engine, tablename="experiences"):
    id = Serial(primary_key=True)
    experience_name = Varchar(length=255, null=False)
    start_year = Varchar(length=20, null=True)
    end_year = Varchar(length=20, null=True)
    ongoing = Boolean(default=False)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("experience_name", "start_year", "end_year", "ongoing", "user")]


class ExperienceBullet(Table, db=engine, tablename="experience_bullets"):
    id = Serial(primary_key=True)
    text = Varchar(length=1024, null=False)
    experience = ForeignKey(Experience)

    class Meta:
        unique_together = [("text", "experience")]


class Project(Table, db=engine, tablename="projects"):
    id = Serial(primary_key=True)
    project_name = Varchar(length=255, null=False)
    github_link = Varchar(length=255, null=True)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("project_name", "github_link", "user")]


class ProjectBullet(Table, db=engine, tablename="project_bullets"):
    id = Serial(primary_key=True)
    text = Varchar(length=1024, null=False)
    project = ForeignKey(Project)

    class Meta:
        unique_together = [("text", "project")]


class Education(Table, db=engine, tablename="education"):
    id = Serial(primary_key=True)
    education_name = Varchar(length=255, null=False)
    institution = Varchar(length=255, null=False)
    start = Varchar(length=50, null=True)
    end = Varchar(length=50, null=True)
    grade = Varchar(length=50, null=True)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("education_name", "institution", "start", "end", "grade", "user")]


class Reference(Table, db=engine, tablename="references"):
    id = Serial(primary_key=True)
    referer_name = Varchar(length=255, null=False)
    referer_institute = Varchar(length=255, null=False)
    position = Varchar(length=255, null=True)
    connection_type = Varchar(length=255, null=True)
    institution_url = Varchar(length=255, null=True)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("referer_name", "referer_institute", "position", "user")]


class Summary(Table, db=engine, tablename="summaries"):
    id = Serial(primary_key=True)
    text = Text(null=False)
    user = ForeignKey(User)

    class Meta:
        unique_together = [("text", "user")]


def create_db_and_tables():
    create_tables(
        User,
        Skill,
        SkillBullet,
        Experience,
        ExperienceBullet,
        Project,
        ProjectBullet,
        Education,
        Reference,
        Summary,
        if_not_exists=True,
    )