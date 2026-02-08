"""
Property-based tests for configuration management.

These tests validate universal correctness properties of the Settings class
and configuration management system.
"""

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from core.config import Settings, get_settings


class TestConfigurationAttributeCompleteness:
    """Property 7: Configuration Attribute Completeness
    
    **Validates: Requirements 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9**
    
    For any Settings class instance, it should have attributes for all required 
    configuration parameters: S3_ACCESS_KEY, S3_SECRET_KEY, S3_ENDPOINT, S3_BUCKET, 
    main_database_url, vector_database_url, redis_url, and CELERY_BROKER_URL.
    """
    
    @given(
        postgres_user=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        postgres_password=st.text(min_size=1, max_size=50),
        postgres_db=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        vector_db=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')),
        s3_endpoint=st.from_regex(r'https?://[a-z0-9.-]+\.[a-z]{2,}', fullmatch=True),
        s3_access_key=st.text(min_size=10, max_size=50),
        s3_secret_key=st.text(min_size=10, max_size=50),
        s3_bucket=st.text(min_size=3, max_size=50, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
    )
    def test_all_required_attributes_present(
        self,
        postgres_user,
        postgres_password,
        postgres_db,
        vector_db,
        s3_endpoint,
        s3_access_key,
        s3_secret_key,
        s3_bucket
    ):
        """Test that Settings instance has all required configuration attributes."""
        # Create Settings instance with valid configuration
        settings = Settings(
            POSTGRES_USER=postgres_user,
            POSTGRES_PASSWORD=postgres_password,
            POSTGRES_DB=postgres_db,
            VECTOR_POSTGRES_DB=vector_db,
            S3_ENDPOINT=s3_endpoint,
            S3_ACCESS_KEY=s3_access_key,
            S3_SECRET_KEY=s3_secret_key,
            S3_BUCKET=s3_bucket,
        )
        
        # Verify all required attributes exist and are accessible
        # Requirement 4.2: S3_KEY (S3_ACCESS_KEY)
        assert hasattr(settings, 'S3_ACCESS_KEY')
        assert settings.S3_ACCESS_KEY == s3_access_key
        
        # Requirement 4.3: S3_SECRET (S3_SECRET_KEY)
        assert hasattr(settings, 'S3_SECRET_KEY')
        assert settings.S3_SECRET_KEY == s3_secret_key
        
        # Requirement 4.4: S3_ENDPOINT
        assert hasattr(settings, 'S3_ENDPOINT')
        assert settings.S3_ENDPOINT == s3_endpoint
        
        # Requirement 4.5: S3_BUCKET
        assert hasattr(settings, 'S3_BUCKET')
        assert settings.S3_BUCKET == s3_bucket
        
        # Requirement 4.6: MAIN_DB_URL (via main_database_url property)
        assert hasattr(settings, 'main_database_url')
        main_db_url = settings.main_database_url
        assert isinstance(main_db_url, str)
        assert postgres_user in main_db_url
        assert postgres_db in main_db_url
        
        # Requirement 4.7: VECTOR_DB_URL (via vector_database_url property)
        assert hasattr(settings, 'vector_database_url')
        vector_db_url = settings.vector_database_url
        assert isinstance(vector_db_url, str)
        assert postgres_user in vector_db_url
        assert vector_db in vector_db_url
        
        # Requirement 4.8: REDIS_URL (via redis_url property)
        assert hasattr(settings, 'redis_url')
        redis_url = settings.redis_url
        assert isinstance(redis_url, str)
        assert redis_url.startswith('redis://')
        
        # Requirement 4.9: CELERY_BROKER_URL (via get_celery_broker_url method)
        assert hasattr(settings, 'get_celery_broker_url')
        celery_broker = settings.get_celery_broker_url()
        assert isinstance(celery_broker, str)
        assert len(celery_broker) > 0
    
    def test_database_url_properties_are_valid_postgresql_urls(self):
        """Test that database URL properties return valid PostgreSQL connection strings."""
        settings = Settings(
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_DB="testdb",
            VECTOR_POSTGRES_DB="vectordb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="access123",
            S3_SECRET_KEY="secret456",
            S3_BUCKET="test-bucket",
        )
        
        # Main database URL should be valid PostgreSQL URL
        main_url = settings.main_database_url
        assert main_url.startswith("postgresql://")
        assert "testuser" in main_url
        assert "testpass" in main_url
        assert "testdb" in main_url
        
        # Vector database URL should be valid PostgreSQL URL
        vector_url = settings.vector_database_url
        assert vector_url.startswith("postgresql://")
        assert "testuser" in vector_url
        assert "testpass" in vector_url
        assert "vectordb" in vector_url
    
    def test_redis_url_property_is_valid_redis_url(self):
        """Test that redis_url property returns valid Redis connection string."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            VECTOR_POSTGRES_DB="vdb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="bucket",
        )
        
        redis_url = settings.redis_url
        assert redis_url.startswith("redis://")
        assert "redis" in redis_url  # Default host
        assert "6379" in redis_url   # Default port


class TestConfigurationDefaultValues:
    """Property 8: Configuration Default Values
    
    **Validates: Requirements 4.10**
    
    For any non-sensitive configuration parameter in the Settings class, 
    it should have a default value defined to allow the system to function 
    with minimal configuration.
    """
    
    def test_non_sensitive_parameters_have_defaults(self):
        """Test that all non-sensitive configuration parameters have default values."""
        # Create Settings with only required parameters
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            VECTOR_POSTGRES_DB="vdb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="bucket",
        )
        
        # Non-sensitive parameters that should have defaults
        # Application settings
        assert settings.APP_NAME == "Fecapass"
        assert settings.APP_VERSION == "1.0.0"
        assert settings.DEBUG is False
        
        # Database hosts and ports
        assert settings.MAIN_DB_HOST == "db_main"
        assert settings.MAIN_DB_PORT == 5432
        assert settings.VECTOR_DB_HOST == "db_vector"
        assert settings.VECTOR_DB_PORT == 5432
        
        # Redis settings
        assert settings.REDIS_HOST == "redis"
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0
        
        # S3 region
        assert settings.S3_REGION == "ru-1"
        
        # Face recognition settings
        assert settings.FACE_DETECTION_THRESHOLD == 0.6
        assert settings.FACE_SIMILARITY_THRESHOLD == 0.7
        assert settings.EMBEDDING_DIMENSION == 512
        
        # Optional Celery settings
        assert settings.CELERY_BROKER_URL is None
        assert settings.CELERY_RESULT_BACKEND is None
    
    @given(
        app_name=st.text(min_size=1, max_size=50),
        debug=st.booleans(),
        redis_host=st.text(min_size=1, max_size=50),
        redis_port=st.integers(min_value=1024, max_value=65535),
    )
    def test_default_values_can_be_overridden(self, app_name, debug, redis_host, redis_port):
        """Test that default values can be overridden with custom values."""
        settings = Settings(
            APP_NAME=app_name,
            DEBUG=debug,
            REDIS_HOST=redis_host,
            REDIS_PORT=redis_port,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            VECTOR_POSTGRES_DB="vdb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="bucket",
        )
        
        # Verify overridden values
        assert settings.APP_NAME == app_name
        assert settings.DEBUG == debug
        assert settings.REDIS_HOST == redis_host
        assert settings.REDIS_PORT == redis_port
    
    def test_celery_urls_default_to_redis_url(self):
        """Test that Celery URLs default to Redis URL when not explicitly set."""
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            VECTOR_POSTGRES_DB="vdb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="bucket",
        )
        
        # When CELERY_BROKER_URL is None, should default to redis_url
        assert settings.CELERY_BROKER_URL is None
        assert settings.get_celery_broker_url() == settings.redis_url
        
        # When CELERY_RESULT_BACKEND is None, should default to redis_url
        assert settings.CELERY_RESULT_BACKEND is None
        assert settings.get_celery_result_backend() == settings.redis_url


class TestConfigurationValidation:
    """Property 9: Configuration Validation
    
    **Validates: Requirements 4.11**
    
    For any attempt to instantiate Settings without required parameters, 
    Pydantic should raise a ValidationError, ensuring all required 
    configuration is present.
    """
    
    def test_missing_postgres_user_raises_validation_error(self):
        """Test that missing POSTGRES_USER raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                # POSTGRES_USER missing
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "POSTGRES_USER" in error_str or "postgres_user" in error_str.lower()
    
    def test_missing_postgres_password_raises_validation_error(self):
        """Test that missing POSTGRES_PASSWORD raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                # POSTGRES_PASSWORD missing
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "POSTGRES_PASSWORD" in error_str or "postgres_password" in error_str.lower()
    
    def test_missing_postgres_db_raises_validation_error(self):
        """Test that missing POSTGRES_DB raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                # POSTGRES_DB missing
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "POSTGRES_DB" in error_str or "postgres_db" in error_str.lower()
    
    def test_missing_vector_postgres_db_raises_validation_error(self):
        """Test that missing VECTOR_POSTGRES_DB raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                # VECTOR_POSTGRES_DB missing
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "VECTOR_POSTGRES_DB" in error_str or "vector_postgres_db" in error_str.lower()
    
    def test_missing_s3_endpoint_raises_validation_error(self):
        """Test that missing S3_ENDPOINT raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                # S3_ENDPOINT missing
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "S3_ENDPOINT" in error_str or "s3_endpoint" in error_str.lower()
    
    def test_missing_s3_access_key_raises_validation_error(self):
        """Test that missing S3_ACCESS_KEY raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                # S3_ACCESS_KEY missing
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "S3_ACCESS_KEY" in error_str or "s3_access_key" in error_str.lower()
    
    def test_missing_s3_secret_key_raises_validation_error(self):
        """Test that missing S3_SECRET_KEY raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                # S3_SECRET_KEY missing
                S3_BUCKET="bucket",
            )
        
        error_str = str(exc_info.value)
        assert "S3_SECRET_KEY" in error_str or "s3_secret_key" in error_str.lower()
    
    def test_missing_s3_bucket_raises_validation_error(self):
        """Test that missing S3_BUCKET raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                # S3_BUCKET missing
            )
        
        error_str = str(exc_info.value)
        assert "S3_BUCKET" in error_str or "s3_bucket" in error_str.lower()
    
    @given(
        threshold=st.floats(min_value=-10.0, max_value=10.0).filter(lambda x: x < 0.0 or x > 1.0)
    )
    def test_invalid_threshold_values_raise_validation_error(self, threshold):
        """Test that threshold values outside [0.0, 1.0] raise ValidationError."""
        with pytest.raises(ValidationError):
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
                FACE_DETECTION_THRESHOLD=threshold,
            )
    
    @given(
        dimension=st.integers(max_value=0)
    )
    def test_invalid_embedding_dimension_raises_validation_error(self, dimension):
        """Test that non-positive embedding dimensions raise ValidationError."""
        with pytest.raises(ValidationError):
            Settings(
                POSTGRES_USER="user",
                POSTGRES_PASSWORD="pass",
                POSTGRES_DB="db",
                VECTOR_POSTGRES_DB="vdb",
                S3_ENDPOINT="https://s3.example.com",
                S3_ACCESS_KEY="key",
                S3_SECRET_KEY="secret",
                S3_BUCKET="bucket",
                EMBEDDING_DIMENSION=dimension,
            )
    
    def test_all_required_fields_present_creates_valid_settings(self):
        """Test that providing all required fields creates a valid Settings instance."""
        # This should NOT raise any exception
        settings = Settings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            VECTOR_POSTGRES_DB="vdb",
            S3_ENDPOINT="https://s3.example.com",
            S3_ACCESS_KEY="key",
            S3_SECRET_KEY="secret",
            S3_BUCKET="bucket",
        )
        
        assert isinstance(settings, Settings)
        assert settings.POSTGRES_USER == "user"
