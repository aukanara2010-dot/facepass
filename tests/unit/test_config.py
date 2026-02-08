"""
Unit tests for core.config module.

Tests cover:
- Loading environment variables
- Default values
- Database URL construction
- Validation of required parameters
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from core.config import Settings, get_settings


class TestSettingsClass:
    """Test suite for Settings class."""
    
    def test_settings_loads_environment_variables(self, monkeypatch):
        """Test that Settings correctly loads all environment variables."""
        # Set all required environment variables
        env_vars = {
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "POSTGRES_DB": "test_main_db",
            "VECTOR_POSTGRES_DB": "test_vector_db",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "S3_BUCKET": "test-bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Create Settings instance
        settings = Settings()
        
        # Verify all variables are loaded correctly
        assert settings.POSTGRES_USER == "test_user"
        assert settings.POSTGRES_PASSWORD == "test_password"
        assert settings.POSTGRES_DB == "test_main_db"
        assert settings.VECTOR_POSTGRES_DB == "test_vector_db"
        assert settings.S3_ENDPOINT == "https://s3.test.com"
        assert settings.S3_ACCESS_KEY == "test_access_key"
        assert settings.S3_SECRET_KEY == "test_secret_key"
        assert settings.S3_BUCKET == "test-bucket"
    
    def test_settings_default_values(self, monkeypatch):
        """Test that Settings applies correct default values for optional parameters."""
        # Set only required environment variables
        required_vars = {
            "POSTGRES_USER": "test_user",
            "POSTGRES_PASSWORD": "test_password",
            "POSTGRES_DB": "test_main_db",
            "VECTOR_POSTGRES_DB": "test_vector_db",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "S3_BUCKET": "test-bucket",
        }
        
        for key, value in required_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        # Verify default values
        assert settings.APP_NAME == "Fecapass"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False
        assert settings.MAIN_DB_HOST == "db_main"
        assert settings.MAIN_DB_PORT == 5432
        assert settings.VECTOR_DB_HOST == "db_vector"
        assert settings.VECTOR_DB_PORT == 5432
        assert settings.REDIS_HOST == "redis"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0
        assert settings.S3_REGION == "ru-1"
        assert settings.FACE_DETECTION_THRESHOLD == 0.6
        assert settings.FACE_SIMILARITY_THRESHOLD == 0.7
        assert settings.EMBEDDING_DIMENSION == 512
        assert settings.CELERY_BROKER_URL is None
        assert settings.CELERY_RESULT_BACKEND is None
    
    def test_main_database_url_construction(self, monkeypatch):
        """Test that main_database_url property constructs correct PostgreSQL URL."""
        env_vars = {
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
            "POSTGRES_DB": "mydb",
            "MAIN_DB_HOST": "localhost",
            "MAIN_DB_PORT": "5433",
            "VECTOR_POSTGRES_DB": "vector_db",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        expected_url = "postgresql://myuser:mypass@localhost:5433/mydb"
        assert settings.main_database_url == expected_url
    
    def test_vector_database_url_construction(self, monkeypatch):
        """Test that vector_database_url property constructs correct PostgreSQL URL."""
        env_vars = {
            "POSTGRES_USER": "vecuser",
            "POSTGRES_PASSWORD": "vecpass",
            "VECTOR_POSTGRES_DB": "vectordb",
            "VECTOR_DB_HOST": "vector-host",
            "VECTOR_DB_PORT": "5434",
            "POSTGRES_DB": "main_db",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        expected_url = "postgresql://vecuser:vecpass@vector-host:5434/vectordb"
        assert settings.vector_database_url == expected_url
    
    def test_redis_url_construction(self, monkeypatch):
        """Test that redis_url property constructs correct Redis URL."""
        env_vars = {
            "REDIS_HOST": "redis-server",
            "REDIS_PORT": "6380",
            "REDIS_DB": "2",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        expected_url = "redis://redis-server:6380/2"
        assert settings.redis_url == expected_url
    
    def test_celery_broker_url_uses_redis_when_not_set(self, monkeypatch):
        """Test that get_celery_broker_url returns redis_url when CELERY_BROKER_URL is not set."""
        env_vars = {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.get_celery_broker_url() == settings.redis_url
    
    def test_celery_broker_url_uses_custom_when_set(self, monkeypatch):
        """Test that get_celery_broker_url returns custom URL when CELERY_BROKER_URL is set."""
        custom_broker = "redis://custom-broker:6379/0"
        env_vars = {
            "CELERY_BROKER_URL": custom_broker,
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.get_celery_broker_url() == custom_broker
    
    def test_celery_result_backend_uses_redis_when_not_set(self, monkeypatch):
        """Test that get_celery_result_backend returns redis_url when CELERY_RESULT_BACKEND is not set."""
        env_vars = {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.get_celery_result_backend() == settings.redis_url
    
    def test_celery_result_backend_uses_custom_when_set(self, monkeypatch):
        """Test that get_celery_result_backend returns custom URL when CELERY_RESULT_BACKEND is set."""
        custom_backend = "redis://custom-backend:6379/1"
        env_vars = {
            "CELERY_RESULT_BACKEND": custom_backend,
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        settings = Settings()
        
        assert settings.get_celery_result_backend() == custom_backend
    
    def test_missing_required_postgres_user_raises_validation_error(self):
        """Test that missing POSTGRES_USER raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.test.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket"
            )
        
        assert "POSTGRES_USER" in str(exc_info.value)
    
    def test_missing_required_postgres_password_raises_validation_error(self):
        """Test that missing POSTGRES_PASSWORD raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.test.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket"
            )
        
        assert "POSTGRES_PASSWORD" in str(exc_info.value)
    
    def test_missing_required_s3_endpoint_raises_validation_error(self):
        """Test that missing S3_ENDPOINT raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket"
            )
        
        assert "S3_ENDPOINT" in str(exc_info.value)
    
    def test_missing_required_s3_access_key_raises_validation_error(self):
        """Test that missing S3_ACCESS_KEY raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.test.com",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket"
            )
        
        assert "S3_ACCESS_KEY" in str(exc_info.value)
    
    def test_invalid_face_detection_threshold_raises_validation_error(self):
        """Test that invalid FACE_DETECTION_THRESHOLD raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.test.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
                FACE_DETECTION_THRESHOLD=1.5  # Invalid: > 1.0
            )
        
        assert "FACE_DETECTION_THRESHOLD" in str(exc_info.value)
    
    def test_invalid_embedding_dimension_raises_validation_error(self):
        """Test that invalid EMBEDDING_DIMENSION raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.test.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
                EMBEDDING_DIMENSION=-1  # Invalid: negative
            )
        
        assert "EMBEDDING_DIMENSION" in str(exc_info.value)


class TestGetSettingsFunction:
    """Test suite for get_settings function."""
    
    def test_get_settings_returns_settings_instance(self, monkeypatch):
        """Test that get_settings returns a Settings instance."""
        env_vars = {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Clear the cache before testing
        get_settings.cache_clear()
        
        settings = get_settings()
        
        assert isinstance(settings, Settings)
    
    def test_get_settings_caches_instance(self, monkeypatch):
        """Test that get_settings returns the same cached instance on multiple calls."""
        env_vars = {
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "db",
            "VECTOR_POSTGRES_DB": "vdb",
            "S3_ENDPOINT": "https://s3.test.com",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
            "S3_BUCKET": "bucket",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Clear the cache before testing
        get_settings.cache_clear()
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        # Should be the exact same instance (same id)
        assert settings1 is settings2
