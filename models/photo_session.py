"""
Photo Session model for external Pixora database integration.

This model represents the photo_sessions table from the main Pixora application
and is used for read-only operations to validate session existence and FacePass status.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid

# Separate base for external Pixora models
PixoraBase = declarative_base()


class PhotoSession(PixoraBase):
    """
    Photo Session model from external Pixora database.
    
    This model is used to validate session existence and check FacePass status
    from the main Pixora application database.
    
    Attributes:
        id (UUID): Primary key, session identifier (UUID)
        name (str): Session name
        description (str): Session description (optional)
        photographer_id (UUID): Photographer identifier
        studio_id (UUID): Studio identifier
        status (str): Session status
        scheduled_at (datetime): Scheduled time (optional)
        completed_at (datetime): Completion time (optional)
        settings (dict): Session settings as JSON (optional)
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        service_package_id (UUID): Service package identifier (optional)
        facepass_enabled (bool): Whether FacePass is enabled for this session
    """
    
    __tablename__ = "photo_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    photographer_id = Column(UUID(as_uuid=True), nullable=False)
    studio_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=False)  # USER-DEFINED type, treating as String
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    service_package_id = Column(UUID(as_uuid=True), nullable=True)
    facepass_enabled = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self) -> str:
        return f"<PhotoSession(id={self.id}, name='{self.name}', facepass_enabled={self.facepass_enabled})>"
    
    def is_facepass_active(self) -> bool:
        """
        Check if FacePass is active for this session.
        
        Returns:
            bool: True if FacePass is enabled, False otherwise
        """
        return self.facepass_enabled is True