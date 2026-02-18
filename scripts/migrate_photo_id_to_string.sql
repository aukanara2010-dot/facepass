-- =====================================================
-- Migration Script: Change photo_id from UUID to VARCHAR
-- =====================================================
-- This script migrates existing tables to use VARCHAR for photo_id
-- instead of UUID to support timestamp-hash format photo IDs
-- =====================================================

-- Backup existing data (optional)
-- CREATE TABLE faces_backup AS SELECT * FROM public.faces;
-- CREATE TABLE face_embeddings_backup AS SELECT * FROM public.face_embeddings;

-- =====================================================
-- Update faces table
-- =====================================================

-- Step 1: Add new column with VARCHAR type
ALTER TABLE public.faces ADD COLUMN photo_id_new VARCHAR(255);

-- Step 2: Copy existing data (convert UUID to string)
UPDATE public.faces SET photo_id_new = photo_id::text WHERE photo_id IS NOT NULL;

-- Step 3: Drop old column and rename new one
ALTER TABLE public.faces DROP COLUMN photo_id;
ALTER TABLE public.faces RENAME COLUMN photo_id_new TO photo_id;

-- Step 4: Add index on new column
CREATE INDEX IF NOT EXISTS idx_faces_photo_id ON public.faces(photo_id);

-- =====================================================
-- Update face_embeddings table
-- =====================================================

-- Step 1: Add new column with VARCHAR type
ALTER TABLE public.face_embeddings ADD COLUMN photo_id_new VARCHAR(255);

-- Step 2: Copy existing data (convert UUID to string)
UPDATE public.face_embeddings SET photo_id_new = photo_id::text WHERE photo_id IS NOT NULL;

-- Step 3: Drop old column and rename new one
ALTER TABLE public.face_embeddings DROP COLUMN photo_id;
ALTER TABLE public.face_embeddings RENAME COLUMN photo_id_new TO photo_id;

-- Step 4: Add index on new column
CREATE INDEX IF NOT EXISTS idx_face_embeddings_photo_id ON public.face_embeddings(photo_id);

-- =====================================================
-- Verification
-- =====================================================

-- Check table structures
\d public.faces;
\d public.face_embeddings;

-- Check data integrity
SELECT 
    'faces' as table_name,
    COUNT(*) as total_rows,
    COUNT(photo_id) as non_null_photo_ids,
    COUNT(DISTINCT photo_id) as unique_photo_ids
FROM public.faces
UNION ALL
SELECT 
    'face_embeddings' as table_name,
    COUNT(*) as total_rows,
    COUNT(photo_id) as non_null_photo_ids,
    COUNT(DISTINCT photo_id) as unique_photo_ids
FROM public.face_embeddings;

-- Sample data
SELECT 'faces sample' as info, id, photo_id, session_id FROM public.faces LIMIT 5;
SELECT 'face_embeddings sample' as info, id, photo_id, session_id FROM public.face_embeddings LIMIT 5;

COMMIT;