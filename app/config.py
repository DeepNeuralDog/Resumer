"""Application configuration using environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Database (Turso)
    DB_URL: str = os.getenv("DB_URL", "")
    DB_TOKEN: str = os.getenv("DB_TOKEN", "")
    
    # JWT Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    
    # LLM Configuration (Anthropic via Azure AI Foundry)
    LLM_API_KEY_ANTHROPIC: str = os.getenv("LLM_API_KEY_ANTHROPIC", "")
    LLM_API_ENDPOINT_ANTHROPIC: str = os.getenv("LLM_API_ENDPOINT_ANTHROPIC", "")
    LLM_DEPLOYMENT_NAME_ANTHROPIC: str = os.getenv("LLM_DEPLOYMENT_NAME_ANTHROPIC", "")
    
    @property
    def has_llm_config(self) -> bool:
        """Check if LLM configuration is available."""
        return bool(self.LLM_API_KEY_ANTHROPIC and self.LLM_API_ENDPOINT_ANTHROPIC)
    
    @property
    def has_db_config(self) -> bool:
        """Check if database configuration is available."""
        return bool(self.DB_URL and self.DB_TOKEN)


settings = Settings()
