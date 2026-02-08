"""
Face Service

This service handles Face-related operations with manual joins to Event data.
Since Face and Event models don't have SQLAlchemy relationships (they may be
in different databases), we handle joins manually at the service layer.
"""

from sqlalchemy.orm import Session
from models.face import Face
from models.event import Event
from typing import Optional, Dict, Any, List


class FaceService:
    """Service for Face-related operations with manual joins"""
    
    @staticmethod
    def get_face_with_event(db: Session, face_id: int) -> Optional[Dict[str, Any]]:
        """
        Get face with event information
        
        Args:
            db: Database session
            face_id: Face ID
            
        Returns:
            Dictionary with face and event data, or None if face not found
        """
        face = db.query(Face).filter(Face.id == face_id).first()
        if not face:
            return None
        
        event = db.query(Event).filter(Event.id == face.event_id).first()
        
        return {
            "face": {
                "id": face.id,
                "event_id": face.event_id,
                "image_url": face.image_url,
                "s3_key": face.s3_key,
                "confidence": face.confidence,
                "created_at": face.created_at
            },
            "event": {
                "id": event.id,
                "event_uuid": str(event.event_uuid),
                "name": event.name,
                "description": event.description,
                "location": event.location,
                "event_date": event.event_date,
                "is_active": event.is_active
            } if event else None
        }
    
    @staticmethod
    def get_event_faces(db: Session, event_id: int) -> List[Face]:
        """
        Get all faces for an event
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            List of Face objects
        """
        return db.query(Face).filter(Face.event_id == event_id).all()
    
    @staticmethod
    def get_faces_with_events(
        db: Session, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all faces with event information using manual JOIN
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of dictionaries with face and event data
        """
        # Manual JOIN
        query = db.query(Face, Event).join(
            Event, Face.event_id == Event.id
        ).offset(skip).limit(limit).all()
        
        results = []
        for face, event in query:
            results.append({
                "face": {
                    "id": face.id,
                    "event_id": face.event_id,
                    "image_url": face.image_url,
                    "s3_key": face.s3_key,
                    "confidence": face.confidence,
                    "created_at": face.created_at
                },
                "event": {
                    "id": event.id,
                    "event_uuid": str(event.event_uuid),
                    "name": event.name,
                    "description": event.description,
                    "location": event.location,
                    "event_date": event.event_date,
                    "is_active": event.is_active
                }
            })
        
        return results
    
    @staticmethod
    def validate_event_exists(db: Session, event_id: int) -> bool:
        """
        Check if event exists
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            True if event exists, False otherwise
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        return event is not None
    
    @staticmethod
    def delete_event_faces(db: Session, event_id: int) -> int:
        """
        Delete all faces for an event (manual cascade delete)
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            Number of deleted faces
        """
        deleted_count = db.query(Face).filter(Face.event_id == event_id).delete()
        db.commit()
        return deleted_count
    
    @staticmethod
    def get_event_stats(db: Session, event_id: int) -> Dict[str, Any]:
        """
        Get statistics for an event
        
        Args:
            db: Database session
            event_id: Event ID
            
        Returns:
            Dictionary with event statistics
        """
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            return None
        
        total_faces = db.query(Face).filter(Face.event_id == event_id).count()
        avg_confidence = db.query(Face).filter(Face.event_id == event_id).with_entities(
            func.avg(Face.confidence)
        ).scalar() or 0.0
        
        return {
            "event_id": event_id,
            "event_uuid": str(event.event_uuid),
            "event_name": event.name,
            "total_photos": total_faces,
            "average_confidence": float(avg_confidence),
            "is_active": event.is_active
        }
