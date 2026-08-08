"""HTML page routes."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.auth import verify_token_for_page


router = APIRouter(tags=["pages"])


def read_html_file(filepath: str) -> str:
    """Read an HTML file and return its contents."""
    with open(filepath) as f:
        return f.read()


def protected_page(request: Request, html_path: str) -> HTMLResponse | RedirectResponse:
    """Return HTML page if authenticated, redirect to login otherwise."""
    if not verify_token_for_page(request):
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie(key="access_token")
        return response
    return HTMLResponse(read_html_file(html_path))


# Public pages
@router.get("/register", response_class=HTMLResponse)
def register_page():
    """Registration page."""
    return HTMLResponse(read_html_file("frontend/register.html"))


@router.get("/login", response_class=HTMLResponse)
def login_page():
    """Login page."""
    return HTMLResponse(read_html_file("frontend/login.html"))


# Protected pages
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Dashboard page (requires authentication)."""
    return protected_page(request, "frontend/dashboard.html")


@router.get("/generate", response_class=HTMLResponse)
def generate_page(request: Request):
    """Resume generation page (requires authentication)."""
    return protected_page(request, "frontend/generate.html")


@router.get("/manage/personal-info", response_class=HTMLResponse)
def manage_personal_info_page(request: Request):
    """Personal info management page (requires authentication)."""
    return protected_page(request, "frontend/manage_personal_info.html")


@router.get("/manage/summaries", response_class=HTMLResponse)
def manage_summaries_page(request: Request):
    """Summaries management page (requires authentication)."""
    return protected_page(request, "frontend/manage_summaries.html")


@router.get("/manage/skills", response_class=HTMLResponse)
def manage_skills_page(request: Request):
    """Skills management page (requires authentication)."""
    return protected_page(request, "frontend/manage_skills.html")


@router.get("/manage/projects", response_class=HTMLResponse)
def manage_projects_page(request: Request):
    """Projects management page (requires authentication)."""
    return protected_page(request, "frontend/manage_projects.html")


@router.get("/manage/experience", response_class=HTMLResponse)
def manage_experience_page(request: Request):
    """Experience management page (requires authentication)."""
    return protected_page(request, "frontend/manage_experience.html")


@router.get("/manage/education", response_class=HTMLResponse)
def manage_education_page(request: Request):
    """Education management page (requires authentication)."""
    return protected_page(request, "frontend/manage_education.html")


@router.get("/manage/references", response_class=HTMLResponse)
def manage_references_page(request: Request):
    """References management page (requires authentication)."""
    return protected_page(request, "frontend/manage_references.html")


@router.get("/favicon.ico")
def favicon():
    """Favicon handler."""
    return JSONResponse({}, status_code=404)
