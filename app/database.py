"""Database connection and operations using Turso serverless."""
from typing import Any, Optional
from contextlib import contextmanager

import turso_serverless

from app.config import settings


def get_connection():
    """Get a connection to the Turso database."""
    return turso_serverless.connect(
        settings.DB_URL,
        auth_token=settings.DB_TOKEN
    )


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(cursor_description: list, row: tuple) -> dict | None:
    """Convert a database row to a dictionary."""
    if row is None:
        return None
    columns = [col[0] for col in cursor_description]
    return dict(zip(columns, row))


def rows_to_dicts(cursor_description: list, rows: list) -> list[dict]:
    """Convert multiple database rows to dictionaries."""
    return [row_to_dict(cursor_description, row) for row in rows]


def fetch_one(conn, query: str, params: tuple = ()) -> dict | None:
    """Execute a query and fetch one row as a dictionary."""
    cursor = conn.execute(query, params)
    row = cursor.fetchone()
    if row is None:
        return None
    return row_to_dict(cursor.description, row)


def fetch_all(conn, query: str, params: tuple = ()) -> list[dict]:
    """Execute a query and fetch all rows as dictionaries."""
    cursor = conn.execute(query, params)
    rows = cursor.fetchall()
    return rows_to_dicts(cursor.description, rows)


def execute(conn, query: str, params: tuple = ()) -> int:
    """Execute a query and return the lastrowid."""
    cursor = conn.execute(query, params)
    conn.commit()
    return cursor.lastrowid


def init_database():
    """Initialize database with schema."""
    with get_db() as conn:
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                phone TEXT,
                location TEXT,
                linkedin TEXT,
                github TEXT,
                website TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Skills table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(skill_name, user_id)
            )
        """)
        
        # Skill bullets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_bullets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                skill_id INTEGER NOT NULL,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
                UNIQUE(text, skill_id)
            )
        """)
        
        # Experiences table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experience_name TEXT NOT NULL,
                start_year TEXT,
                end_year TEXT,
                ongoing INTEGER DEFAULT 0,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Experience bullets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experience_bullets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                experience_id INTEGER NOT NULL,
                FOREIGN KEY (experience_id) REFERENCES experiences(id) ON DELETE CASCADE,
                UNIQUE(text, experience_id)
            )
        """)
        
        # Projects table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                github_link TEXT,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Project bullets table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_bullets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                project_id INTEGER NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                UNIQUE(text, project_id)
            )
        """)
        
        # Education table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS education (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                education_name TEXT NOT NULL,
                institution TEXT NOT NULL,
                start TEXT,
                end TEXT,
                grade TEXT,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # References table (using 'user_references' since 'references' is a reserved keyword)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referer_name TEXT NOT NULL,
                referer_institute TEXT NOT NULL,
                position TEXT,
                connection_type TEXT,
                institution_url TEXT,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Summaries table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(text, user_id)
            )
        """)
        
        conn.commit()


# =============================================================================
# USER CRUD OPERATIONS
# =============================================================================

def get_user_by_email(conn, email: str) -> dict | None:
    """Get a user by email."""
    return fetch_one(conn, "SELECT * FROM users WHERE email = ?", (email,))


def get_user_by_id(conn, user_id: int) -> dict | None:
    """Get a user by ID."""
    return fetch_one(conn, "SELECT * FROM users WHERE id = ?", (user_id,))


def create_user(conn, name: str, email: str, password_hash: str, 
                phone: str = None, location: str = None, linkedin: str = None,
                github: str = None, website: str = None) -> int:
    """Create a new user and return the user ID."""
    cursor = conn.execute(
        """INSERT INTO users (name, email, password_hash, phone, location, linkedin, github, website)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (name, email, password_hash, phone, location, linkedin, github, website)
    )
    conn.commit()
    return cursor.lastrowid


def update_user(conn, user_id: int, name: str, email: str, phone: str = None,
                location: str = None, linkedin: str = None, github: str = None,
                website: str = None, password_hash: str = None) -> None:
    """Update a user's profile."""
    if password_hash:
        conn.execute(
            """UPDATE users SET name = ?, email = ?, phone = ?, location = ?, 
               linkedin = ?, github = ?, website = ?, password_hash = ? WHERE id = ?""",
            (name, email, phone, location, linkedin, github, website, password_hash, user_id)
        )
    else:
        conn.execute(
            """UPDATE users SET name = ?, email = ?, phone = ?, location = ?, 
               linkedin = ?, github = ?, website = ? WHERE id = ?""",
            (name, email, phone, location, linkedin, github, website, user_id)
        )
    conn.commit()


# =============================================================================
# SUMMARIES CRUD OPERATIONS
# =============================================================================

def get_summaries(conn, user_id: int, query: str = None) -> list[dict]:
    """Get all summaries for a user, optionally filtered by query."""
    if query:
        return fetch_all(
            conn,
            "SELECT * FROM summaries WHERE user = ? AND text LIKE ? ORDER BY id DESC",
            (user_id, f"%{query}%")
        )
    return fetch_all(
        conn, 
        "SELECT * FROM summaries WHERE user = ? ORDER BY id DESC", 
        (user_id,)
    )


def get_summary_by_id(conn, summary_id: int, user_id: int) -> dict | None:
    """Get a summary by ID and user ID."""
    return fetch_one(
        conn, 
        "SELECT * FROM summaries WHERE id = ? AND user = ?", 
        (summary_id, user_id)
    )


def get_summary_by_text(conn, text: str, user_id: int) -> dict | None:
    """Get a summary by text and user ID."""
    return fetch_one(
        conn, 
        "SELECT * FROM summaries WHERE text = ? AND user = ?", 
        (text, user_id)
    )


def create_summary(conn, text: str, user_id: int) -> int:
    """Create a new summary and return its ID."""
    cursor = conn.execute(
        "INSERT INTO summaries (text, user) VALUES (?, ?)",
        (text, user_id)
    )
    conn.commit()
    return cursor.lastrowid


def update_summary(conn, summary_id: int, text: str) -> None:
    """Update a summary's text."""
    conn.execute("UPDATE summaries SET text = ? WHERE id = ?", (text, summary_id))
    conn.commit()


def delete_summary(conn, summary_id: int) -> None:
    """Delete a summary."""
    conn.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
    conn.commit()


# =============================================================================
# SKILLS CRUD OPERATIONS
# =============================================================================

def get_skills(conn, user_id: int, query: str = None) -> list[dict]:
    """Get all skills for a user with their bullets."""
    if query:
        skills = fetch_all(
            conn,
            "SELECT * FROM skills WHERE user = ? AND skill_name LIKE ? ORDER BY id DESC",
            (user_id, f"%{query}%")
        )
    else:
        skills = fetch_all(
            conn, 
            "SELECT * FROM skills WHERE user = ? ORDER BY id DESC", 
            (user_id,)
        )
    
    # Fetch bullets for each skill
    for skill in skills:
        bullets = fetch_all(
            conn,
            "SELECT text FROM skill_bullets WHERE skill = ?",
            (skill["id"],)
        )
        skill["bullet_points"] = [b["text"] for b in bullets]
    
    return skills


def get_skill_by_id(conn, skill_id: int, user_id: int) -> dict | None:
    """Get a skill by ID and user ID."""
    skill = fetch_one(
        conn, 
        "SELECT * FROM skills WHERE id = ? AND user = ?", 
        (skill_id, user_id)
    )
    if skill:
        bullets = fetch_all(
            conn,
            "SELECT text FROM skill_bullets WHERE skill = ?",
            (skill_id,)
        )
        skill["bullet_points"] = [b["text"] for b in bullets]
    return skill


def get_skill_by_name(conn, skill_name: str, user_id: int) -> dict | None:
    """Get a skill by name and user ID."""
    return fetch_one(
        conn, 
        "SELECT * FROM skills WHERE skill_name = ? AND user = ?", 
        (skill_name, user_id)
    )


def create_skill(conn, skill_name: str, user_id: int, bullet_points: list[str] = None) -> int:
    """Create a new skill with bullets and return its ID."""
    cursor = conn.execute(
        "INSERT INTO skills (skill_name, user) VALUES (?, ?)",
        (skill_name, user_id)
    )
    skill_id = cursor.lastrowid
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO skill_bullets (text, skill) VALUES (?, ?)",
                (point, skill_id)
            )
    
    conn.commit()
    return skill_id


def update_skill(conn, skill_id: int, skill_name: str, bullet_points: list[str] = None) -> None:
    """Update a skill's name and bullets."""
    conn.execute("UPDATE skills SET skill_name = ? WHERE id = ?", (skill_name, skill_id))
    
    # Delete existing bullets and re-insert
    conn.execute("DELETE FROM skill_bullets WHERE skill = ?", (skill_id,))
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO skill_bullets (text, skill) VALUES (?, ?)",
                (point, skill_id)
            )
    
    conn.commit()


def delete_skill(conn, skill_id: int) -> None:
    """Delete a skill (bullets will cascade)."""
    conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
    conn.commit()


def get_skill_bullets(conn, skill_id: int, query: str = None) -> list[str]:
    """Get bullets for a skill, optionally filtered by query."""
    if query:
        bullets = fetch_all(
            conn,
            "SELECT text FROM skill_bullets WHERE skill = ? AND text LIKE ?",
            (skill_id, f"%{query}%")
        )
    else:
        bullets = fetch_all(
            conn,
            "SELECT text FROM skill_bullets WHERE skill = ?",
            (skill_id,)
        )
    return [b["text"] for b in bullets]


# =============================================================================
# EXPERIENCES CRUD OPERATIONS
# =============================================================================

def get_experiences(conn, user_id: int, query: str = None) -> list[dict]:
    """Get all experiences for a user with their bullets."""
    if query:
        experiences = fetch_all(
            conn,
            "SELECT * FROM experiences WHERE user = ? AND experience_name LIKE ? ORDER BY id DESC",
            (user_id, f"%{query}%")
        )
    else:
        experiences = fetch_all(
            conn, 
            "SELECT * FROM experiences WHERE user = ? ORDER BY id DESC", 
            (user_id,)
        )
    
    # Fetch bullets for each experience
    for exp in experiences:
        bullets = fetch_all(
            conn,
            "SELECT text FROM experience_bullets WHERE experience = ?",
            (exp["id"],)
        )
        exp["bullet_points"] = [b["text"] for b in bullets]
    
    return experiences


def get_experience_by_id(conn, experience_id: int, user_id: int) -> dict | None:
    """Get an experience by ID and user ID."""
    exp = fetch_one(
        conn, 
        "SELECT * FROM experiences WHERE id = ? AND user = ?", 
        (experience_id, user_id)
    )
    if exp:
        bullets = fetch_all(
            conn,
            "SELECT text FROM experience_bullets WHERE experience = ?",
            (experience_id,)
        )
        exp["bullet_points"] = [b["text"] for b in bullets]
    return exp


def get_experience_by_details(conn, experience_name: str, start_year: str, 
                               end_year: str, user_id: int) -> dict | None:
    """Get an experience by details."""
    return fetch_one(
        conn,
        """SELECT * FROM experiences WHERE experience_name = ? AND start_year = ? 
           AND end_year = ? AND user = ?""",
        (experience_name, start_year, end_year, user_id)
    )


def create_experience(conn, experience_name: str, user_id: int, 
                      start_year: str = None, end_year: str = None,
                      bullet_points: list[str] = None) -> int:
    """Create a new experience with bullets and return its ID."""
    cursor = conn.execute(
        "INSERT INTO experiences (experience_name, start_year, end_year, user) VALUES (?, ?, ?, ?)",
        (experience_name, start_year, end_year, user_id)
    )
    exp_id = cursor.lastrowid
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO experience_bullets (text, experience) VALUES (?, ?)",
                (point, exp_id)
            )
    
    conn.commit()
    return exp_id


def update_experience(conn, experience_id: int, experience_name: str,
                     start_year: str = None, end_year: str = None,
                     bullet_points: list[str] = None) -> None:
    """Update an experience's details and bullets."""
    conn.execute(
        "UPDATE experiences SET experience_name = ?, start_year = ?, end_year = ? WHERE id = ?",
        (experience_name, start_year, end_year, experience_id)
    )
    
    # Delete existing bullets and re-insert
    conn.execute("DELETE FROM experience_bullets WHERE experience = ?", (experience_id,))
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO experience_bullets (text, experience) VALUES (?, ?)",
                (point, experience_id)
            )
    
    conn.commit()


def delete_experience(conn, experience_id: int) -> None:
    """Delete an experience (bullets will cascade)."""
    conn.execute("DELETE FROM experiences WHERE id = ?", (experience_id,))
    conn.commit()


def get_experience_bullets(conn, experience_id: int, query: str = None) -> list[str]:
    """Get bullets for an experience, optionally filtered by query."""
    if query:
        bullets = fetch_all(
            conn,
            "SELECT text FROM experience_bullets WHERE experience = ? AND text LIKE ?",
            (experience_id, f"%{query}%")
        )
    else:
        bullets = fetch_all(
            conn,
            "SELECT text FROM experience_bullets WHERE experience = ?",
            (experience_id,)
        )
    return [b["text"] for b in bullets]


# =============================================================================
# PROJECTS CRUD OPERATIONS
# =============================================================================

def get_projects(conn, user_id: int, query: str = None) -> list[dict]:
    """Get all projects for a user with their bullets."""
    if query:
        projects = fetch_all(
            conn,
            "SELECT * FROM projects WHERE user = ? AND project_name LIKE ? ORDER BY id DESC",
            (user_id, f"%{query}%")
        )
    else:
        projects = fetch_all(
            conn, 
            "SELECT * FROM projects WHERE user = ? ORDER BY id DESC", 
            (user_id,)
        )
    
    # Fetch bullets for each project
    for proj in projects:
        bullets = fetch_all(
            conn,
            "SELECT text FROM project_bullets WHERE project = ?",
            (proj["id"],)
        )
        proj["bullet_points"] = [b["text"] for b in bullets]
    
    return projects


def get_project_by_id(conn, project_id: int, user_id: int) -> dict | None:
    """Get a project by ID and user ID."""
    proj = fetch_one(
        conn, 
        "SELECT * FROM projects WHERE id = ? AND user = ?", 
        (project_id, user_id)
    )
    if proj:
        bullets = fetch_all(
            conn,
            "SELECT text FROM project_bullets WHERE project = ?",
            (project_id,)
        )
        proj["bullet_points"] = [b["text"] for b in bullets]
    return proj


def get_project_by_details(conn, project_name: str, github_link: str, user_id: int) -> dict | None:
    """Get a project by details."""
    return fetch_one(
        conn,
        "SELECT * FROM projects WHERE project_name = ? AND github_link = ? AND user = ?",
        (project_name, github_link, user_id)
    )


def create_project(conn, project_name: str, user_id: int, 
                   github_link: str = None, bullet_points: list[str] = None) -> int:
    """Create a new project with bullets and return its ID."""
    cursor = conn.execute(
        "INSERT INTO projects (project_name, github_link, user) VALUES (?, ?, ?)",
        (project_name, github_link, user_id)
    )
    proj_id = cursor.lastrowid
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO project_bullets (text, project) VALUES (?, ?)",
                (point, proj_id)
            )
    
    conn.commit()
    return proj_id


def update_project(conn, project_id: int, project_name: str,
                   github_link: str = None, bullet_points: list[str] = None) -> None:
    """Update a project's details and bullets."""
    conn.execute(
        "UPDATE projects SET project_name = ?, github_link = ? WHERE id = ?",
        (project_name, github_link, project_id)
    )
    
    # Delete existing bullets and re-insert
    conn.execute("DELETE FROM project_bullets WHERE project = ?", (project_id,))
    
    if bullet_points:
        for point in bullet_points:
            conn.execute(
                "INSERT INTO project_bullets (text, project) VALUES (?, ?)",
                (point, project_id)
            )
    
    conn.commit()


def delete_project(conn, project_id: int) -> None:
    """Delete a project (bullets will cascade)."""
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()


def get_project_bullets(conn, project_id: int, query: str = None) -> list[str]:
    """Get bullets for a project, optionally filtered by query."""
    if query:
        bullets = fetch_all(
            conn,
            "SELECT text FROM project_bullets WHERE project = ? AND text LIKE ?",
            (project_id, f"%{query}%")
        )
    else:
        bullets = fetch_all(
            conn,
            "SELECT text FROM project_bullets WHERE project = ?",
            (project_id,)
        )
    return [b["text"] for b in bullets]


# =============================================================================
# EDUCATION CRUD OPERATIONS
# =============================================================================

def get_educations(conn, user_id: int, query: str = None) -> list[dict]:
    """Get all education entries for a user."""
    if query:
        return fetch_all(
            conn,
            """SELECT * FROM education WHERE user = ? AND 
               (education_name LIKE ? OR institution LIKE ?) ORDER BY id DESC""",
            (user_id, f"%{query}%", f"%{query}%")
        )
    return fetch_all(
        conn, 
        "SELECT * FROM education WHERE user = ? ORDER BY id DESC", 
        (user_id,)
    )


def get_education_by_id(conn, education_id: int, user_id: int) -> dict | None:
    """Get an education entry by ID and user ID."""
    return fetch_one(
        conn, 
        "SELECT * FROM education WHERE id = ? AND user = ?", 
        (education_id, user_id)
    )


def get_education_by_details(conn, education_name: str, institution: str,
                             start: str, end: str, grade: str, user_id: int) -> dict | None:
    """Get an education entry by details."""
    return fetch_one(
        conn,
        """SELECT * FROM education WHERE education_name = ? AND institution = ? 
           AND start = ? AND end = ? AND grade = ? AND user = ?""",
        (education_name, institution, start, end, grade, user_id)
    )


def create_education(conn, education_name: str, institution: str, user_id: int,
                     start: str = None, end: str = None, grade: str = None) -> int:
    """Create a new education entry and return its ID."""
    cursor = conn.execute(
        "INSERT INTO education (education_name, institution, start, end, grade, user) VALUES (?, ?, ?, ?, ?, ?)",
        (education_name, institution, start, end, grade, user_id)
    )
    conn.commit()
    return cursor.lastrowid


def update_education(conn, education_id: int, education_name: str, institution: str,
                     start: str = None, end: str = None, grade: str = None) -> None:
    """Update an education entry."""
    conn.execute(
        "UPDATE education SET education_name = ?, institution = ?, start = ?, end = ?, grade = ? WHERE id = ?",
        (education_name, institution, start, end, grade, education_id)
    )
    conn.commit()


def delete_education(conn, education_id: int) -> None:
    """Delete an education entry."""
    conn.execute("DELETE FROM education WHERE id = ?", (education_id,))
    conn.commit()


# =============================================================================
# REFERENCES CRUD OPERATIONS
# =============================================================================

def get_references(conn, user_id: int) -> list[dict]:
    """Get all references for a user."""
    return fetch_all(
        conn, 
        "SELECT * FROM user_references WHERE user = ? ORDER BY id DESC", 
        (user_id,)
    )


def get_reference_by_id(conn, reference_id: int, user_id: int) -> dict | None:
    """Get a reference by ID and user ID."""
    return fetch_one(
        conn, 
        "SELECT * FROM user_references WHERE id = ? AND user = ?", 
        (reference_id, user_id)
    )


def get_reference_by_details(conn, referer_name: str, referer_institute: str,
                             position: str, connection_type: str, 
                             institution_url: str, user_id: int) -> dict | None:
    """Get a reference by details."""
    return fetch_one(
        conn,
        """SELECT * FROM user_references WHERE referer_name = ? AND referer_institute = ? 
           AND position = ? AND connection_type = ? AND institution_url = ? AND user = ?""",
        (referer_name, referer_institute, position, connection_type, institution_url, user_id)
    )


def create_reference(conn, referer_name: str, referer_institute: str, user_id: int,
                     position: str = None, connection_type: str = None,
                     institution_url: str = None) -> int:
    """Create a new reference and return its ID."""
    cursor = conn.execute(
        """INSERT INTO user_references (referer_name, referer_institute, position, 
           connection_type, institution_url, user) VALUES (?, ?, ?, ?, ?, ?)""",
        (referer_name, referer_institute, position, connection_type, institution_url, user_id)
    )
    conn.commit()
    return cursor.lastrowid


def update_reference(conn, reference_id: int, referer_name: str, referer_institute: str,
                     position: str = None, connection_type: str = None,
                     institution_url: str = None) -> None:
    """Update a reference."""
    conn.execute(
        """UPDATE user_references SET referer_name = ?, referer_institute = ?, position = ?, 
           connection_type = ?, institution_url = ? WHERE id = ?""",
        (referer_name, referer_institute, position, connection_type, institution_url, reference_id)
    )
    conn.commit()


def delete_reference(conn, reference_id: int) -> None:
    """Delete a reference."""
    conn.execute("DELETE FROM user_references WHERE id = ?", (reference_id,))
    conn.commit()
