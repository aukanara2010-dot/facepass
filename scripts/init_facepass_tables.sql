-- =====================================================
-- FacePass Database Initialization Script
-- =====================================================
-- This script creates the necessary tables for FacePass
-- Run this on your LOCAL vector database server
-- =====================================================

-- Enable pgvector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS public;

-- =====================================================
-- Main Database Tables (faces table)
-- =====================================================
-- Note: Run this on your MAIN database if needed

-- DROP TABLE IF EXISTS public.faces CASCADE;

CREATE TABLE IF NOT EXISTS public.faces (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NULL,                          -- For legacy events (optional)
    session_id UUID NULL,                           -- For Pixora sessions (UUID)
    photo_id VARCHAR(255) NULL,                     -- Reference to photos.id (can be UUID or timestamp-hash format)
    image_url VARCHAR NOT NULL,                     -- S3 URL of the image
    s3_key VARCHAR NOT NULL,                        -- S3 object key
    confidence FLOAT NOT NULL DEFAULT 0.0,         -- Face detection confidence (0.0-1.0)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for faces table
CREATE INDEX IF NOT EXISTS idx_faces_event_id ON public.faces(event_id);
CREATE INDEX IF NOT EXISTS idx_faces_session_id ON public.faces(session_id);
CREATE INDEX IF NOT EXISTS idx_faces_photo_id ON public.faces(photo_id);
CREATE INDEX IF NOT EXISTS idx_faces_created_at ON public.faces(created_at);

-- =====================================================
-- Vector Database Tables (face_embeddings table)
-- =====================================================
-- Note: Run this on your LOCAL vector database

-- DROP TABLE IF EXISTS public.face_embeddings CASCADE;

CREATE TABLE IF NOT EXISTS public.face_embeddings (
    id SERIAL PRIMARY KEY,
    face_id INTEGER NULL,                           -- Reference to faces.id (optional)
    photo_id VARCHAR(255) NULL,                     -- Direct reference to photos.id (can be UUID or timestamp-hash format)
    event_id INTEGER NULL,                          -- For legacy events (optional)
    session_id UUID NULL,                           -- For Pixora sessions (UUID)
    embedding vector(512) NOT NULL,                 -- 512-dimensional face embedding
    confidence FLOAT NULL,                          -- Face detection confidence (0.0-1.0)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for face_embeddings table
CREATE INDEX IF NOT EXISTS idx_face_embeddings_face_id ON public.face_embeddings(face_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_photo_id ON public.face_embeddings(photo_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_event_id ON public.face_embeddings(event_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_id ON public.face_embeddings(session_id);
CREATE INDEX IF NOT EXISTS idx_face_embeddings_created_at ON public.face_embeddings(created_at);

-- Vector similarity index (HNSW for fast similarity search)
CREATE INDEX IF NOT EXISTS idx_face_embeddings_embedding_hnsw 
ON public.face_embeddings 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Alternative: IVFFlat index (use if HNSW is not available)
-- CREATE INDEX IF NOT EXISTS idx_face_embeddings_embedding_ivfflat 
-- ON public.face_embeddings 
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);

-- =====================================================
-- Sample Data for Testing (Optional)
-- =====================================================

-- Insert sample face embedding for testing
-- Note: This is just for testing - replace with real data
/*
INSERT INTO public.face_embeddings (
    photo_id, 
    session_id, 
    embedding, 
    confidence
) VALUES (
    '1788875f-fc71-49d6-a9fa-a060e3ee6fee'::uuid,  -- Sample photo ID
    '1788875f-fc71-49d6-a9fa-a060e3ee6fee'::uuid,  -- Sample session ID
    array_fill(0.1, ARRAY[512])::vector(512),       -- Sample embedding (all 0.1)
    0.95                                             -- High confidence
);
*/

-- =====================================================
-- Verification Queries
-- =====================================================

-- Check if tables were created successfully
SELECT 
    schemaname, 
    tablename, 
    tableowner 
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('faces', 'face_embeddings');

-- Check if pgvector extension is installed
SELECT 
    extname, 
    extversion 
FROM pg_extension 
WHERE extname = 'vector';

-- Check indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND tablename IN ('faces', 'face_embeddings')
ORDER BY tablename, indexname;

-- Check table structures
\d public.faces;
\d public.face_embeddings;

-- =====================================================
-- Performance Optimization
-- =====================================================

-- Update table statistics for better query planning
ANALYZE public.faces;
ANALYZE public.face_embeddings;

-- Set work_mem for better vector operations (adjust based on your RAM)
-- SET work_mem = '256MB';

-- =====================================================
-- Cleanup Commands (Use with caution!)
-- =====================================================

-- Uncomment these lines if you need to reset the tables
-- WARNING: This will delete all data!

/*
DROP TABLE IF EXISTS public.face_embeddings CASCADE;
DROP TABLE IF EXISTS public.faces CASCADE;
*/

-- =====================================================
-- Usage Examples
-- =====================================================

-- Example: Insert a face embedding
/*
INSERT INTO public.face_embeddings (
    photo_id,
    session_id,
    embedding,
    confidence
) VALUES (
    'your-photo-uuid-here'::uuid,
    'your-session-uuid-here'::uuid,
    '[0.1,0.2,0.3,...]'::vector(512),  -- Your actual 512-dim embedding
    0.95
);
*/

-- Example: Search for similar faces
/*
SELECT 
    photo_id,
    session_id,
    1 - (embedding <=> '[0.1,0.2,0.3,...]'::vector(512)) as similarity
FROM public.face_embeddings
WHERE session_id = 'your-session-uuid'::uuid
    AND (1 - (embedding <=> '[0.1,0.2,0.3,...]'::vector(512))) >= 0.6
ORDER BY embedding <=> '[0.1,0.2,0.3,...]'::vector(512) ASC
LIMIT 10;
*/

-- =====================================================
-- Monitoring Queries
-- =====================================================

-- Count records by session
SELECT 
    session_id,
    COUNT(*) as embedding_count
FROM public.face_embeddings 
WHERE session_id IS NOT NULL
GROUP BY session_id
ORDER BY embedding_count DESC;

-- Check embedding dimensions
SELECT 
    id,
    photo_id,
    vector_dims(embedding) as dimensions
FROM public.face_embeddings 
LIMIT 5;

-- Performance check for similarity search
EXPLAIN ANALYZE
SELECT 
    photo_id,
    1 - (embedding <=> '[0.1,0.2,0.3]'::vector(3)) as similarity
FROM public.face_embeddings
WHERE session_id = '1788875f-fc71-49d6-a9fa-a060e3ee6fee'::uuid
ORDER BY embedding <=> '[0.1,0.2,0.3]'::vector(3) ASC
LIMIT 10;

COMMIT;