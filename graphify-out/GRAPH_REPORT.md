# Graph Report - .  (2026-08-03)

## Corpus Check
- Corpus is ~16,940 words - fits in a single context window. You may not need a graph.

## Summary
- 156 nodes · 325 edges · 21 communities (10 shown, 11 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 3 edges (avg confidence: 0.77)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Resume Data Models
- API Read Endpoints
- CRUD Operations
- Frontend Pages
- Database Layer
- Authentication
- Deployment Config
- ATS Optimization
- Login/Register UI
- PDF Generation
- Logout Flow
- Template Loading
- Security Libraries
- JSON Download
- JSON Import
- Autocomplete
- FastAPI Core
- Jinja Templating
- Image Processing
- Data Validation

## God Nodes (most connected - your core abstractions)
1. `fetch_one()` - 27 edges
2. `save_resume_data()` - 14 edges
3. `generate_pdf()` - 10 edges
4. `Meta` - 9 edges
5. `Experience` - 8 edges
6. `run_ats_optimization()` - 8 edges
7. `Dashboard Page` - 8 edges
8. `Skill` - 7 edges
9. `Project` - 7 edges
10. `run_ats_gaps()` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Uvicorn ASGI Server` --semantically_similar_to--> `Uvicorn ASGI Server`  [INFERRED] [semantically similar]
  README.md → requirements.txt
- `register_user()` --calls--> `User`  [EXTRACTED]
  main.py → database.py
- `create_skill()` --calls--> `SkillBullet`  [EXTRACTED]
  main.py → database.py
- `save_resume_data()` --calls--> `SkillBullet`  [EXTRACTED]
  main.py → database.py
- `update_skill()` --calls--> `SkillBullet`  [EXTRACTED]
  main.py → database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Authentication Flow** — frontend_login_login_page, frontend_register_register_page, api_login_endpoint, api_register_endpoint, api_logout_endpoint, requirements_python_jose, requirements_passlib [INFERRED 0.85]
- **Resume Data Management Pages** — frontend_manage_education_manage_education_page, frontend_manage_experience_manage_experience_page, frontend_manage_personal_info_manage_personal_info_page, frontend_manage_projects_manage_projects_page, frontend_manage_references_manage_references_page, frontend_manage_skills_manage_skills_page, frontend_manage_summaries_manage_summaries_page [INFERRED 0.85]
- **PDF Generation Flow** — frontend_generate_generatepdf, api_generate_pdf_endpoint, readme_typst_typesetting, requirements_pillow [INFERRED 0.75]

## Communities (21 total, 11 thin omitted)

### Community 0 - "Resume Data Models"
Cohesion: 0.11
Nodes (30): BaseModel, ats_gaps(), ats_optimize(), ATSGapsResponse, ATSOptimizeRequest, ATSResumeData, Contact, create_education() (+22 more)

### Community 1 - "API Read Endpoints"
Cohesion: 0.16
Nodes (28): get, dashboard(), favicon(), generate_page(), get_current_user(), get_educations(), get_experience_bullets(), get_experiences() (+20 more)

### Community 2 - "CRUD Operations"
Cohesion: 0.18
Nodes (21): delete, create_summary(), delete_education(), delete_experience(), delete_project(), delete_reference(), delete_skill(), delete_summary() (+13 more)

### Community 3 - "Frontend Pages"
Cohesion: 0.11
Nodes (19): /api/educations Endpoint, /api/experiences Endpoint, /api/projects Endpoint, /api/references Endpoint, /api/skills Endpoint, /api/summaries Endpoint, /api/user-profile Endpoint, Dashboard Page (+11 more)

### Community 4 - "Database Layer"
Cohesion: 0.24
Nodes (16): create_db_and_tables(), Education, Experience, ExperienceBullet, Meta, Project, ProjectBullet, Reference (+8 more)

### Community 5 - "Authentication"
Cohesion: 0.40
Nodes (6): authenticate_user(), create_access_token(), login(), UserLogin, verify_password(), timedelta

### Community 6 - "Deployment Config"
Cohesion: 0.33
Nodes (6): Resumer Project, Typst Typesetting System, uv Dependency Manager, Uvicorn ASGI Server, Render Deployment Configuration, Uvicorn ASGI Server

### Community 7 - "ATS Optimization"
Cohesion: 0.40
Nodes (5): /api/ats-gaps Endpoint, /api/ats-optimize Endpoint, ATS Optimization Feature, findMissingSkills Function, optimizeATS Function

### Community 8 - "Login/Register UI"
Cohesion: 0.50
Nodes (4): /api/login Endpoint, /api/register Endpoint, Login Page, Registration Page

## Knowledge Gaps
- **31 isolated node(s):** `uv Dependency Manager`, `Typst Typesetting System`, `fetchUserProfile Function`, `logout Function`, `Resume Generation Page` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fetch_one()` connect `CRUD Operations` to `Resume Data Models`, `API Read Endpoints`, `Authentication`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Why does `save_resume_data()` connect `Resume Data Models` to `API Read Endpoints`, `CRUD Operations`, `Database Layer`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **What connects `uv Dependency Manager`, `Typst Typesetting System`, `fetchUserProfile Function` to the rest of the system?**
  _31 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Resume Data Models` be split into smaller, more focused modules?**
  _Cohesion score 0.11363636363636363 - nodes in this community are weakly interconnected._
- **Should `Frontend Pages` be split into smaller, more focused modules?**
  _Cohesion score 0.10526315789473684 - nodes in this community are weakly interconnected._