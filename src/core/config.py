"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agent Flight Recorder"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API & CORS
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://app_user:app_password@localhost:5432/baseline"
    
    # Security
    JWT_SECRET: str = "insecure-dev-secret-change-in-production-00000000"
    JWT_ALGORITHM: str = "HS256"
    OIDC_ISSUER: str = "https://auth.example.com"
    OIDC_CLIENT_ID: str = "afr-client"
    
    # Storage
    ARTIFACT_STORAGE_PATH: str = "/tmp/artifacts"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
