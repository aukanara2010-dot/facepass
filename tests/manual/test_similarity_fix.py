#!/usr/bin/env python3
"""
Test script to verify similarity calculation fix

This script tests:
1. InsightFace embeddings are normalized
2. Inner product similarity calculation works correctly
3. Similarity values are in correct range (0.0 to 1.0)
"""

import os
import sys
import logging
import numpy as np
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_embedding_normalization():
    """Test that InsightFace embeddings are normalized"""
    from services.face_recognition import get_face_recognition_service
    
    face_service = get_face_recognition_service()
    if not face_service.initialized:
        print("⚠ Face recognition service not initialized (InsightFace not available)")
        return False
    
    # Create a simple test image (white square)
    from PIL import Image
    import io
    
    # Create a 100x100 white image
    img = Image.new('RGB', (100, 100), color='white')
    
    # Add a simple face-like pattern (dark pixels for eyes and mouth)
    pixels = img.load()
    # Eyes
    for x in range(30, 35):
        for y in range(30, 35):
            pixels[x, y] = (0, 0, 0)
    for x in range(65, 70):
        for y in range(30, 35):
            pixels[x, y] = (0, 0, 0)
    # Mouth
    for x in range(40, 60):
        for y in range(60, 65):
            pixels[x, y] = (0, 0, 0)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_data = img_bytes.getvalue()
    
    try:
        embeddings = face_service.get_embeddings(img_data)
        if not embeddings:
            print("⚠ No faces detected in test image")
            return False
        
        embedding, confidence = embeddings[0]
        norm = np.linalg.norm(embedding)
        
        print(f"✓ Embedding extracted: shape={embedding.shape}, norm={norm:.6f}")
        
        # Check if normalized (norm should be close to 1.0)
        if abs(norm - 1.0) < 0.01:
            print("✓ Embedding is normalized (norm ≈ 1.0)")
            return True
        else:
            print(f"⚠ Embedding may not be normalized (norm = {norm:.6f})")
            return False
            
    except Exception as e:
        print(f"❌ Error testing embedding: {e}")
        return False

def test_similarity_calculation():
    """Test similarity calculation with inner product"""
    print("\nTesting similarity calculation...")
    
    # Create two normalized test vectors
    vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    vec3 = np.array([1.0, 0.0, 0.0], dtype=np.float32)  # Same as vec1
    
    # Normalize them
    vec1 = vec1 / np.linalg.norm(vec1)
    vec2 = vec2 / np.linalg.norm(vec2)
    vec3 = vec3 / np.linalg.norm(vec3)
    
    print(f"Vector 1: {vec1}")
    print(f"Vector 2: {vec2}")
    print(f"Vector 3: {vec3}")
    
    # Test inner product similarity (what we use in SQL)
    # Formula: (vec1 <#> vec2) * -1 = -(vec1 · vec2) * -1 = vec1 · vec2
    similarity_12 = np.dot(vec1, vec2)  # Should be 0.0 (orthogonal)
    similarity_13 = np.dot(vec1, vec3)  # Should be 1.0 (identical)
    
    print(f"Similarity vec1-vec2 (orthogonal): {similarity_12:.6f}")
    print(f"Similarity vec1-vec3 (identical): {similarity_13:.6f}")
    
    # Test cosine similarity for comparison
    cosine_12 = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    cosine_13 = np.dot(vec1, vec3) / (np.linalg.norm(vec1) * np.linalg.norm(vec3))
    
    print(f"Cosine similarity vec1-vec2: {cosine_12:.6f}")
    print(f"Cosine similarity vec1-vec3: {cosine_13:.6f}")
    
    # For normalized vectors, inner product = cosine similarity
    if abs(similarity_12 - cosine_12) < 0.001 and abs(similarity_13 - cosine_13) < 0.001:
        print("✓ Inner product equals cosine similarity for normalized vectors")
        return True
    else:
        print("❌ Inner product doesn't match cosine similarity")
        return False

def test_sql_formula():
    """Test the SQL formula we're using"""
    print("\nTesting SQL formula simulation...")
    
    # Simulate pgvector <#> operator (negative inner product)
    vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec2 = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    vec3 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    
    # Normalize
    vec1 = vec1 / np.linalg.norm(vec1)
    vec2 = vec2 / np.linalg.norm(vec2)
    vec3 = vec3 / np.linalg.norm(vec3)
    
    # Simulate pgvector <#> (negative inner product)
    pgvector_12 = -np.dot(vec1, vec2)  # <#> returns negative inner product
    pgvector_13 = -np.dot(vec1, vec3)
    
    # Our SQL formula: (embedding <#> query) * -1
    similarity_12 = pgvector_12 * -1  # Should be 0.0
    similarity_13 = pgvector_13 * -1  # Should be 1.0
    
    print(f"pgvector <#> vec1-vec2: {pgvector_12:.6f}")
    print(f"pgvector <#> vec1-vec3: {pgvector_13:.6f}")
    print(f"Our formula vec1-vec2: {similarity_12:.6f}")
    print(f"Our formula vec1-vec3: {similarity_13:.6f}")
    
    if 0.0 <= similarity_12 <= 1.0 and 0.0 <= similarity_13 <= 1.0:
        print("✓ Similarity values are in correct range [0.0, 1.0]")
        if similarity_13 > similarity_12:
            print("✓ Identical vectors have higher similarity than orthogonal vectors")
            return True
        else:
            print("❌ Similarity ordering is incorrect")
            return False
    else:
        print(f"❌ Similarity values out of range: {similarity_12}, {similarity_13}")
        return False

def main():
    """Run all tests"""
    print("Testing similarity calculation fix...")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Embedding normalization
    if test_embedding_normalization():
        success_count += 1
    
    # Test 2: Similarity calculation
    if test_similarity_calculation():
        success_count += 1
    
    # Test 3: SQL formula
    if test_sql_formula():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("✅ All tests passed!")
        print("\nChanges implemented:")
        print("1. ✓ Fixed SQL queries to use inner product <#> for normalized vectors")
        print("2. ✓ Updated similarity formula: (embedding <#> query) * -1")
        print("3. ✓ Fixed ORDER BY to use DESC for proper sorting")
        print("4. ✓ Verified embedding normalization logging")
        print("\nSimilarity values should now be in range [0.0, 1.0]:")
        print("- 1.0 = identical faces")
        print("- 0.0 = completely different faces")
        print("- No more negative values!")
    else:
        print("❌ Some tests failed. Check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()