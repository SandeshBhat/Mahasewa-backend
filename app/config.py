"""
MahaSeWA Backend - Configuration Management
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    model_config = ConfigDict(
        extra='ignore',  # Ignore extra env vars not in model
        env_file=".env",
        case_sensitive=True
    )
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    APP_NAME: str = "MahaSeWA API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # ========================================================================
    # DATABASE
    # ========================================================================
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mahasewa_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_ECHO: bool = False
    
    # ========================================================================
    # SECURITY & AUTHENTICATION
    # ========================================================================
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12
    
    # ========================================================================
    # CORS
    # ========================================================================
    CORS_ORIGINS: List[str] = [
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
        "https://mahasewa.vercel.app",  # Vercel production
        "https://mahasewa.org",
        "https://www.mahasewa.org",
        "https://mahasewa-kz7u8lbgx-hyperneural.vercel.app",  # Vercel auto-generated
        "https://mahasewa.vercel.app",  # Vercel production domain
        "https://*.vercel.app",  # All Vercel preview deployments
    ]
    ALLOWED_HOSTS: List[str] = [
        "localhost",
        "127.0.0.1",
        "mahasewa.org",
        "www.mahasewa.org",
        "*"  # For Railway/Render deployment
    ]
    
    # ========================================================================
    # REDIS
    # ========================================================================
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 10
    
    # ========================================================================
    # EMAIL
    # ========================================================================
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "noreply@mahasewa.org"
    EMAIL_FROM_NAME: str = "MahaSeWA"
    
    # ========================================================================
    # AWS S3
    # ========================================================================
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "mahasewa-files"
    AWS_REGION: str = "ap-south-1"
    
    # ========================================================================
    # FILE UPLOAD (VPS-based)
    # ========================================================================
    UPLOAD_BASE_DIR: str = os.getenv("UPLOAD_BASE_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
    STATIC_URL_PREFIX: str = os.getenv("STATIC_URL_PREFIX", "/static")
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [
        "pdf", "doc", "docx", "xls", "xlsx",
        "jpg", "jpeg", "png", "gif"
    ]
    
    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # ========================================================================
    # MONITORING
    # ========================================================================
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    
    # ========================================================================
    # THIRD-PARTY APIs
    # ========================================================================
    GOOGLE_MAPS_API_KEY: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    
    # ========================================================================
    # BUSINESS LOGIC
    # ========================================================================
    PROVIDER_VERIFICATION_SLA_HOURS: int = 72
    FIRST_CONSULTATION_FREE: bool = True
    DEFAULT_CONSULTATION_DURATION: int = 30
    
    # Config moved to model_config above (Pydantic v2)
    
    @property
    def database_url_sync(self) -> str:
        """
        Synchronous database URL for SQLAlchemy
        """
        return self.DATABASE_URL
    
    @property
    def database_url_async(self) -> str:
        """
        Asynchronous database URL for async operations
        """
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


# Create global settings instance
settings = Settings()

