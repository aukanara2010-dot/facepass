"""
Celery task definitions for FacePass background processing.

Tasks are auto-discovered by the Celery worker via the `include` setting
in `core.celery_app`. Each task runs in its own DB session that is
properly closed after the task completes (success or failure).
"""

import logging

from core.celery_app import celery_app
from core.database import SessionLocal
from services.indexing import IndexingService

logger = logging.getLogger(__name__)


@celery_app.task(name="sync_s3_photos_task")
def sync_s3_photos_task(session_id: str) -> None:
    """
    Background task: download photos from S3 for *session_id*, extract face
    embeddings and persist them to the vector database.

    Args:
        session_id: UUID of the photo session to index.
    """
    logger.info("Start background indexing for %s", session_id)

    db = SessionLocal()
    try:
        service = IndexingService()
        success, indexed_count, error = service.load_embeddings_from_s3(
            session_id=session_id,
            db=db,
        )

        if success:
            logger.info(
                "Finish background indexing for %s — %d photo(s) indexed",
                session_id,
                indexed_count,
            )
        else:
            logger.error(
                "Finish background indexing for %s with error: %s",
                session_id,
                error,
            )
    except Exception as exc:
        logger.exception(
            "Unhandled exception during background indexing for %s: %s",
            session_id,
            exc,
        )
        raise
    finally:
        db.close()
