"""
Unit tests for models (SQLAlchemy and Pydantic).

Tests cover:
- SQLAlchemy model instantiation
- Pydantic schema validation
- Schema serialization/deserialization
- Field constraints and defaults
"""

import os
import pytest
from datetime import datetime
from pydantic import ValidationError

# Set up test environment variables before importing models
os.environ.setdefault('POSTGRES_USER', 'test_user')
os.environ.setdefault('POSTGRES_PASSWORD', 'test_password')
os.environ.setdefault('POSTGRES_DB', 'test_db')
os.environ.setdefault('VECTOR_POSTGRES_DB', 'test_vector_db')
os.environ.setdefault('S3_ENDPOINT', 'https://test.s3.com')
os.environ.setdefault('S3_ACCESS_KEY', 'test_access_key')
os.environ.setdefault('S3_SECRET_KEY', 'test_secret_key')
os.environ.setdefault('S3_BUCKET', 'test_bucket')

from models.user import User
from models.face import Face, FaceEmbedding
from app.schemas.face import (
    FaceUploadRequest,
    FaceUploadResponse,
    FaceSearchRequest,
    FaceSearchResult,
    FaceSearchResponse
)


class TestUserModel:
    """Test suite for User SQLAlchemy model."""
    
    def test_user_model_creation(self):
        """Test that User model can be instantiated with required fields."""
        user = User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
        
        assert user.id == 1
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
    
    def test_user_model_with_minimal_fields(self):
        """Test that User model can be created with only required fields."""
        user = User(
            email="minimal@example.com"
        )
        
        assert user.email == "minimal@example.com"
        assert user.full_name is None
        assert user.is_active is True  # Default value
    
    def test_user_model_has_tablename(self):
        """Test that User model has correct table name."""
        assert User.__tablename__ == "users"
    
    def test_user_model_has_schema(self):
        """Test that User model has correct schema."""
        assert User.__table_args__ == {'schema': 'public'}
    
    def test_user_model_email_is_required(self):
        """Test that email field is required (nullable=False)."""
        # Check column definition
        email_column = User.__table__.columns['email']
        assert email_column.nullable is False
    
    def test_user_model_email_is_unique(self):
        """Test that email field has unique constraint."""
        email_column = User.__table__.columns['email']
        assert email_column.unique is True
    
    def test_user_model_email_is_indexed(self):
        """Test that email field is indexed."""
        email_column = User.__table__.columns['email']
        assert email_column.index is True
    
    def test_user_model_full_name_is_optional(self):
        """Test that full_name field is optional (nullable=True)."""
        full_name_column = User.__table__.columns['full_name']
        assert full_name_column.nullable is True
    
    def test_user_model_is_active_has_default(self):
        """Test that is_active field has default value."""
        is_active_column = User.__table__.columns['is_active']
        assert is_active_column.default is not None
    
    def test_user_model_has_timestamps(self):
        """Test that User model has created_at and updated_at fields."""
        assert 'created_at' in User.__table__.columns
        assert 'updated_at' in User.__table__.columns


class TestFaceModel:
    """Test suite for Face SQLAlchemy model."""
    
    def test_face_model_creation(self):
        """Test that Face model can be instantiated with required fields."""
        face = Face(
            id=1,
            user_id=1,
            image_url="https://s3.example.com/image.jpg",
            s3_key="faces/image.jpg",
            confidence=0.95
        )
        
        assert face.id == 1
        assert face.user_id == 1
        assert face.image_url == "https://s3.example.com/image.jpg"
        assert face.s3_key == "faces/image.jpg"
        assert face.confidence == 0.95
    
    def test_face_model_has_tablename(self):
        """Test that Face model has correct table name."""
        assert Face.__tablename__ == "faces"
    
    def test_face_model_has_schema(self):
        """Test that Face model has correct schema."""
        assert Face.__table_args__ == {'schema': 'public'}
    
    def test_face_model_user_id_is_required(self):
        """Test that user_id field is required (nullable=False)."""
        user_id_column = Face.__table__.columns['user_id']
        assert user_id_column.nullable is False
    
    def test_face_model_image_url_is_required(self):
        """Test that image_url field is required (nullable=False)."""
        image_url_column = Face.__table__.columns['image_url']
        assert image_url_column.nullable is False
    
    def test_face_model_s3_key_is_required(self):
        """Test that s3_key field is required (nullable=False)."""
        s3_key_column = Face.__table__.columns['s3_key']
        assert s3_key_column.nullable is False
    
    def test_face_model_confidence_is_required(self):
        """Test that confidence field is required (nullable=False)."""
        confidence_column = Face.__table__.columns['confidence']
        assert confidence_column.nullable is False
    
    def test_face_model_has_foreign_key(self):
        """Test that Face model has foreign key to users table."""
        user_id_column = Face.__table__.columns['user_id']
        assert len(user_id_column.foreign_keys) > 0
        fk = list(user_id_column.foreign_keys)[0]
        assert 'users.id' in str(fk.target_fullname)
    
    def test_face_model_has_created_at(self):
        """Test that Face model has created_at timestamp."""
        assert 'created_at' in Face.__table__.columns


class TestFaceEmbeddingModel:
    """Test suite for FaceEmbedding SQLAlchemy model."""
    
    def test_face_embedding_model_creation(self):
        """Test that FaceEmbedding model can be instantiated with required fields."""
        # Note: We can't test actual vector values without a database connection
        face_embedding = FaceEmbedding(
            id=1,
            face_id=1
        )
        
        assert face_embedding.id == 1
        assert face_embedding.face_id == 1
    
    def test_face_embedding_model_has_tablename(self):
        """Test that FaceEmbedding model has correct table name."""
        assert FaceEmbedding.__tablename__ == "face_embeddings"
    
    def test_face_embedding_model_has_schema(self):
        """Test that FaceEmbedding model has correct schema."""
        assert FaceEmbedding.__table_args__ == {'schema': 'public'}
    
    def test_face_embedding_model_face_id_is_required(self):
        """Test that face_id field is required (nullable=False)."""
        face_id_column = FaceEmbedding.__table__.columns['face_id']
        assert face_id_column.nullable is False
    
    def test_face_embedding_model_face_id_is_indexed(self):
        """Test that face_id field is indexed."""
        face_id_column = FaceEmbedding.__table__.columns['face_id']
        assert face_id_column.index is True
    
    def test_face_embedding_model_embedding_is_required(self):
        """Test that embedding field is required (nullable=False)."""
        embedding_column = FaceEmbedding.__table__.columns['embedding']
        assert embedding_column.nullable is False
    
    def test_face_embedding_model_has_created_at(self):
        """Test that FaceEmbedding model has created_at timestamp."""
        assert 'created_at' in FaceEmbedding.__table__.columns


class TestFaceUploadRequestSchema:
    """Test suite for FaceUploadRequest Pydantic schema."""
    
    def test_face_upload_request_valid_data(self):
        """Test that FaceUploadRequest accepts valid data."""
        request = FaceUploadRequest(user_id=1)
        
        assert request.user_id == 1
    
    def test_face_upload_request_rejects_zero_user_id(self):
        """Test that FaceUploadRequest rejects user_id of 0."""
        with pytest.raises(ValidationError) as exc_info:
            FaceUploadRequest(user_id=0)
        
        assert "user_id" in str(exc_info.value).lower()
    
    def test_face_upload_request_rejects_negative_user_id(self):
        """Test that FaceUploadRequest rejects negative user_id."""
        with pytest.raises(ValidationError) as exc_info:
            FaceUploadRequest(user_id=-1)
        
        assert "user_id" in str(exc_info.value).lower()
    
    def test_face_upload_request_requires_user_id(self):
        """Test that FaceUploadRequest requires user_id field."""
        with pytest.raises(ValidationError) as exc_info:
            FaceUploadRequest()
        
        assert "user_id" in str(exc_info.value).lower()


class TestFaceUploadResponseSchema:
    """Test suite for FaceUploadResponse Pydantic schema."""
    
    def test_face_upload_response_valid_data(self):
        """Test that FaceUploadResponse accepts valid data."""
        response = FaceUploadResponse(
            face_id=1,
            image_url="https://s3.example.com/image.jpg",
            confidence=0.95,
            task_id="abc123"
        )
        
        assert response.face_id == 1
        assert response.image_url == "https://s3.example.com/image.jpg"
        assert response.confidence == 0.95
        assert response.task_id == "abc123"
    
    def test_face_upload_response_confidence_bounds(self):
        """Test that FaceUploadResponse validates confidence bounds."""
        # Valid confidence at lower bound
        response = FaceUploadResponse(
            face_id=1,
            image_url="https://s3.example.com/image.jpg",
            confidence=0.0,
            task_id="abc123"
        )
        assert response.confidence == 0.0
        
        # Valid confidence at upper bound
        response = FaceUploadResponse(
            face_id=1,
            image_url="https://s3.example.com/image.jpg",
            confidence=1.0,
            task_id="abc123"
        )
        assert response.confidence == 1.0
    
    def test_face_upload_response_rejects_invalid_confidence(self):
        """Test that FaceUploadResponse rejects confidence outside [0, 1]."""
        # Test confidence > 1
        with pytest.raises(ValidationError) as exc_info:
            FaceUploadResponse(
                face_id=1,
                image_url="https://s3.example.com/image.jpg",
                confidence=1.5,
                task_id="abc123"
            )
        assert "confidence" in str(exc_info.value).lower()
        
        # Test confidence < 0
        with pytest.raises(ValidationError) as exc_info:
            FaceUploadResponse(
                face_id=1,
                image_url="https://s3.example.com/image.jpg",
                confidence=-0.1,
                task_id="abc123"
            )
        assert "confidence" in str(exc_info.value).lower()


class TestFaceSearchRequestSchema:
    """Test suite for FaceSearchRequest Pydantic schema."""
    
    def test_face_search_request_with_defaults(self):
        """Test that FaceSearchRequest uses default values."""
        request = FaceSearchRequest()
        
        assert request.threshold == 0.7
        assert request.limit == 10
    
    def test_face_search_request_with_custom_values(self):
        """Test that FaceSearchRequest accepts custom values."""
        request = FaceSearchRequest(threshold=0.8, limit=20)
        
        assert request.threshold == 0.8
        assert request.limit == 20
    
    def test_face_search_request_threshold_bounds(self):
        """Test that FaceSearchRequest validates threshold bounds."""
        # Valid at lower bound
        request = FaceSearchRequest(threshold=0.0)
        assert request.threshold == 0.0
        
        # Valid at upper bound
        request = FaceSearchRequest(threshold=1.0)
        assert request.threshold == 1.0
    
    def test_face_search_request_rejects_invalid_threshold(self):
        """Test that FaceSearchRequest rejects threshold outside [0, 1]."""
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchRequest(threshold=1.5)
        assert "threshold" in str(exc_info.value).lower()
        
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchRequest(threshold=-0.1)
        assert "threshold" in str(exc_info.value).lower()
    
    def test_face_search_request_limit_bounds(self):
        """Test that FaceSearchRequest validates limit bounds."""
        # Valid at lower bound
        request = FaceSearchRequest(limit=1)
        assert request.limit == 1
        
        # Valid at upper bound
        request = FaceSearchRequest(limit=100)
        assert request.limit == 100
    
    def test_face_search_request_rejects_invalid_limit(self):
        """Test that FaceSearchRequest rejects limit outside [1, 100]."""
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchRequest(limit=0)
        assert "limit" in str(exc_info.value).lower()
        
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchRequest(limit=101)
        assert "limit" in str(exc_info.value).lower()


class TestFaceSearchResultSchema:
    """Test suite for FaceSearchResult Pydantic schema."""
    
    def test_face_search_result_valid_data(self):
        """Test that FaceSearchResult accepts valid data."""
        result = FaceSearchResult(
            face_id=1,
            user_id=1,
            similarity=0.95,
            image_url="https://s3.example.com/image.jpg"
        )
        
        assert result.face_id == 1
        assert result.user_id == 1
        assert result.similarity == 0.95
        assert result.image_url == "https://s3.example.com/image.jpg"
    
    def test_face_search_result_similarity_bounds(self):
        """Test that FaceSearchResult validates similarity bounds."""
        # Valid at lower bound
        result = FaceSearchResult(
            face_id=1,
            user_id=1,
            similarity=0.0,
            image_url="https://s3.example.com/image.jpg"
        )
        assert result.similarity == 0.0
        
        # Valid at upper bound
        result = FaceSearchResult(
            face_id=1,
            user_id=1,
            similarity=1.0,
            image_url="https://s3.example.com/image.jpg"
        )
        assert result.similarity == 1.0
    
    def test_face_search_result_rejects_invalid_similarity(self):
        """Test that FaceSearchResult rejects similarity outside [0, 1]."""
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchResult(
                face_id=1,
                user_id=1,
                similarity=1.5,
                image_url="https://s3.example.com/image.jpg"
            )
        assert "similarity" in str(exc_info.value).lower()


class TestFaceSearchResponseSchema:
    """Test suite for FaceSearchResponse Pydantic schema."""
    
    def test_face_search_response_valid_data(self):
        """Test that FaceSearchResponse accepts valid data."""
        results = [
            FaceSearchResult(
                face_id=1,
                user_id=1,
                similarity=0.95,
                image_url="https://s3.example.com/image1.jpg"
            ),
            FaceSearchResult(
                face_id=2,
                user_id=2,
                similarity=0.85,
                image_url="https://s3.example.com/image2.jpg"
            )
        ]
        
        response = FaceSearchResponse(
            results=results,
            query_time_ms=123.45
        )
        
        assert len(response.results) == 2
        assert response.query_time_ms == 123.45
    
    def test_face_search_response_empty_results(self):
        """Test that FaceSearchResponse accepts empty results list."""
        response = FaceSearchResponse(
            results=[],
            query_time_ms=50.0
        )
        
        assert len(response.results) == 0
        assert response.query_time_ms == 50.0
    
    def test_face_search_response_rejects_negative_query_time(self):
        """Test that FaceSearchResponse rejects negative query_time_ms."""
        with pytest.raises(ValidationError) as exc_info:
            FaceSearchResponse(
                results=[],
                query_time_ms=-10.0
            )
        assert "query_time_ms" in str(exc_info.value).lower()
    
    def test_face_search_response_serialization(self):
        """Test that FaceSearchResponse can be serialized to dict."""
        results = [
            FaceSearchResult(
                face_id=1,
                user_id=1,
                similarity=0.95,
                image_url="https://s3.example.com/image.jpg"
            )
        ]
        
        response = FaceSearchResponse(
            results=results,
            query_time_ms=100.0
        )
        
        data = response.model_dump()
        
        assert isinstance(data, dict)
        assert "results" in data
        assert "query_time_ms" in data
        assert len(data["results"]) == 1
        assert data["query_time_ms"] == 100.0
