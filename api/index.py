"""Vercel serverless entry point for FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app import database as db
from app.llm import init_llm_client

# Import all routers
from app.routes import auth, profile, summaries, skills, experiences, projects, educations, references, ats, pdf, pages


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    # Startup
    logger.info("Starting up application...")
    
    # Initialize database tables
    try:
        db.init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Initialize LLM client
    try:
        if settings.has_llm_config:
            init_llm_client()
            logger.info("LLM client initialized successfully")
        else:
            logger.warning("LLM client configuration missing - ATS optimization will be unavailable")
    except Exception as e:
        logger.warning(f"LLM client initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="Resumer API",
    description="Resume builder with ATS optimization",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include all routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(summaries.router)
app.include_router(skills.router)
app.include_router(experiences.router)
app.include_router(projects.router)
app.include_router(educations.router)
app.include_router(references.router)
app.include_router(ats.router)
app.include_router(pdf.router)
app.include_router(pages.router)


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"}


# For local development with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
