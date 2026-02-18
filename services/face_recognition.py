"""
Face recognition service using InsightFace

This module handles:
- Face detection
- Face embedding extraction (512-dimensional vectors)
- Face quality assessment
"""

import numpy as np
from typing import Optional, List, Tuple
import io
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """
    Service for face detection and embedding extraction using InsightFace
    
    Uses buffalo_l model which provides:
    - High accuracy face detection
    - 512-dimensional face embeddings
    - Good performance on various face angles and lighting
    """
    
    def __init__(self):
        """Initialize InsightFace model"""
        try:
            import insightface
            from insightface.app import FaceAnalysis
            
            logger.info("Initializing InsightFace with buffalo_l model...")
            self.app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=-1, det_size=(640, 640))
            logger.info("InsightFace initialized successfully")
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            logger.warning("Face recognition will not work until InsightFace is properly installed")
            self.initialized = False
            self.app = None
    
    def _bytes_to_image(self, image_data: bytes) -> np.ndarray:
        """
        Convert image bytes to numpy array (BGR format for OpenCV/InsightFace)
        
        Args:
            image_data: Image binary data
            
        Returns:
            numpy array in BGR format
        """
        # Load image with PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Convert RGB to BGR (OpenCV/InsightFace format)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return img_bgr
    
    def get_embeddings(self, image_data: bytes) -> List[Tuple[np.ndarray, float]]:
        """
        Extract face embeddings from image
        
        Finds all faces in the image and returns their embeddings.
        
        Args:
            image_data: Image binary data
            
        Returns:
            List of tuples (embedding_vector, confidence_score)
            Returns empty list if no faces detected
            
        Raises:
            RuntimeError: If InsightFace is not initialized
            ValueError: If image cannot be processed
        """
        if not self.initialized or self.app is None:
            raise RuntimeError("InsightFace is not initialized. Check installation and logs.")
        
        try:
            # Convert bytes to image array
            img = self._bytes_to_image(image_data)
            
            # Detect faces and extract embeddings
            faces = self.app.get(img)
            
            if len(faces) == 0:
                logger.info("No faces detected in image")
                return []
            
            # Extract embeddings and confidence scores
            results = []
            for face in faces:
                embedding = face.embedding  # 512-dimensional vector
                confidence = float(face.det_score)  # Detection confidence
                
                # Verify embedding is normalized (InsightFace should provide normalized embeddings)
                norm = np.linalg.norm(embedding)
                logger.debug(f"Embedding norm: {norm:.6f} (should be ~1.0 for normalized vectors)")
                
                results.append((embedding, confidence))
                logger.debug(f"Detected face with confidence: {confidence:.3f} using buffalo_l model")
            
            logger.info(f"Extracted {len(results)} face embedding(s) using buffalo_l model")
            return results
            
        except Exception as e:
            logger.error(f"Error extracting embeddings: {e}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def extract_single_embedding(self, image_data: bytes) -> Tuple[Optional[np.ndarray], float]:
        """
        Extract embedding from image (expects single face)
        
        Args:
            image_data: Image binary data
            
        Returns:
            Tuple of (embedding vector, confidence score)
            Returns (None, 0.0) if no face detected
            
        Raises:
            RuntimeError: If InsightFace is not initialized
            ValueError: If multiple faces detected or image cannot be processed
        """
        embeddings = self.get_embeddings(image_data)
        
        if len(embeddings) == 0:
            logger.warning("No face detected in image")
            return None, 0.0
        
        if len(embeddings) > 1:
            logger.warning(f"Multiple faces detected ({len(embeddings)}), using first face")
            # Could also raise ValueError here if strict single-face requirement
        
        return embeddings[0]
    
    def compare_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compare two face embeddings using cosine similarity
        
        Args:
            embedding1: First embedding vector (512-dim)
            embedding2: Second embedding vector (512-dim)
            
        Returns:
            Similarity score (0.0 to 1.0, higher = more similar)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        similarity = dot_product / (norm1 * norm2)
        
        # Convert from [-1, 1] to [0, 1]
        normalized_similarity = (similarity + 1) / 2
        
        return float(normalized_similarity)


# Singleton instance
_face_recognition_service: Optional[FaceRecognitionService] = None


def get_face_recognition_service() -> FaceRecognitionService:
    """Get or create FaceRecognitionService singleton"""
    global _face_recognition_service
    if _face_recognition_service is None:
        _face_recognition_service = FaceRecognitionService()
    return _face_recognition_service
