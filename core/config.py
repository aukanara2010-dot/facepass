"""
Configuration management module for Fecapass application.

This module provides centralized configuration management using pydantic-settings
for loading and validating environment variables from .env file.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All required configuration parameters must be provided via environment variables
    or .env file. Optional parameters have sensible defaults.
    """
    
    # Application Settings
    APP_NAME: str = "FacePass"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Domain configuration
    DOMAIN: str = "facepass.pixorasoft.ru"
    STAGING_DOMAIN: str = "staging.pixorasoft.ru"
    
    # Database - Main (Required fields)
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    MAIN_DB_HOST: str = "db_main"
    MAIN_DB_PORT: int = 5432
    
    # Database - Vector (Required fields)
    VECTOR_DB_HOST: str = "db_vector"
    VECTOR_DB_PORT: int = 5432
    VECTOR_POSTGRES_DB: str
    
    # Redis (Default values provided)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Celery (Optional, will use Redis URL if not provided)
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # S3 Storage (Required fields)
    S3_ENDPOINT: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_REGION: str = "ru-1"
    
    # External Pixora Database
    MAIN_APP_DATABASE_URL: str
    
    # Face Recognition Settings (Default values provided)
    FACE_DETECTION_THRESHOLD: float = Field(default=0.6, ge=0.0, le=1.0)
    FACE_SIMILARITY_THRESHOLD: float = Field(default=0.7, ge=0.0, le=1.0)
    EMBEDDING_DIMENSION: int = 512
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    @field_validator("FACE_DETECTION_THRESHOLD", "FACE_SIMILARITY_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate that threshold values are between 0.0 and 1.0."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator("EMBEDDING_DIMENSION")
    @classmethod
    def validate_embedding_dimension(cls, v: int) -> int:
        """Validate that embedding dimension is positive."""
        if v <= 0:
            raise ValueError("Embedding dimension must be positive")
        return v
    
    @property
    def main_database_url(self) -> str:
        """
        Construct PostgreSQL connection URL for main database.
        
        Returns:
            str: SQLAlchemy-compatible database URL
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.MAIN_DB_HOST}:{self.MAIN_DB_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def vector_database_url(self) -> str:
        """
        Construct PostgreSQL connection URL for vector database.
        
        Returns:
            str: SQLAlchemy-compatible database URL
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.VECTOR_DB_HOST}:{self.VECTOR_DB_PORT}/{self.VECTOR_POSTGRES_DB}"
        )
    
    @property
    def redis_url(self) -> str:
        """
        Construct Redis connection URL.
        
        Returns:
            str: Redis connection URL
        """
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def get_celery_broker_url(self) -> str:
        """
        Get Celery broker URL, defaulting to Redis URL if not explicitly set.
        
        Returns:
            str: Celery broker URL
        """
        return self.CELERY_BROKER_URL or self.redis_url
    
    def get_celery_result_backend(self) -> str:
        """
        Get Celery result backend URL, defaulting to Redis URL if not explicitly set.
        
        Returns:
            str: Celery result backend URL
        """
        return self.CELERY_RESULT_BACKEND or self.redis_url


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached Settings instance.
    
    This function uses lru_cache to ensure only one Settings instance is created
    and reused throughout the application lifecycle.
    
    Returns:
        Settings: Singleton Settings instance
    """
    return Settings()
