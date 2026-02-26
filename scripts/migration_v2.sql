-- Facepass Microservice Isolation - Database Migration v2.0
-- This script migrates face_embeddings table to simplified schema
-- 
-- Changes:
-- 1. Remove face_id column (reference to deleted Face model)
-- 2. Remove event_id column (legacy event-based architecture)
-- 3. Add NOT NULL constraints to photo_id and session_id
-- 4. Add unique constraint to prevent duplicates
-- 5. Recreate indexes for optimal performance
-- 6. Create vector index for similarity search
--
-- IMPORTANT: Run backup_database.sh BEFORE executing this migration!

BEGIN;

-- Step 1: Create backup table
CREATE TABLE IF NOT EXISTS face_embeddings_backup AS 
SELECT * FROM face_embeddings;

COMMENT ON TABLE face_embeddings_backup IS 'Backup before v2.0 migration - created at ' || NOW();

-- Step 2: Verify data before migration
DO $$
DECLARE
    total_count INTEGER;
    null_session_count INTEGER;
    null_photo_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM face_embeddings;
    SELECT COUNT(*) INTO null_session_count FROM face_embeddings WHERE session_id IS NULL;
    SELECT COUNT(*) INTO null_photo_count FROM face_embeddings WHERE photo_id IS NULL;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration Pre-Check';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Total embeddings: %', total_count;
    RAISE NOTICE 'Embeddings with NULL session_id: %', null_session_count;
    RAISE NOTICE 'Embeddings with NULL photo_id: %', null_photo_count;
    RAISE NOTICE '';
    
    IF null_session_count > 0 THEN
        RAISE WARNING 'Found % embeddings with NULL session_id - these will be deleted', null_session_count;
    END IF;
    
    IF null_photo_count > 0 THEN
        RAISE WARNING 'Found % embeddings with NULL photo_id - these will be deleted', null_photo_count;
    END IF;
END $$;

-- Step 3: Delete embeddings without session_id or photo_id (legacy event-based data)
DELETE FROM face_embeddings WHERE session_id IS NULL OR photo_id IS NULL;

-- Step 4: Drop old indexes
DROP INDEX IF EXISTS idx_face_embeddings_face_id;
DROP INDEX IF EXISTS idx_face_embeddings_event_id;
DROP INDEX IF EXISTS idx_face_embeddings_vector;  -- Will recreate with better parameters

-- Step 5: Drop unused columns
ALTER TABLE face_embeddings DROP COLUMN IF EXISTS face_id;
ALTER TABLE face_embeddings DROP COLUMN IF EXISTS event_id;

-- Step 6: Add NOT NULL constraints
ALTER TABLE face_embeddings 
    ALTER COLUMN photo_id SET NOT NULL,
    ALTER COLUMN session_id SET NOT NULL,
    ALTER COLUMN embedding SET NOT NULL,
    ALTER COLUMN confidence SET NOT NULL;

-- Step 7: Add unique constraint (prevent duplicate embeddings for same photo)
-- Note: This will fail if duplicates exist - clean them up first
DO $$
BEGIN
    ALTER TABLE face_embeddings 
        ADD CONSTRAINT unique_photo_session UNIQUE (photo_id, session_id);
    RAISE NOTICE 'Added unique constraint: unique_photo_session';
EXCEPTION
    WHEN unique_violation THEN
        RAISE WARNING 'Unique constraint already exists or duplicates found';
        RAISE WARNING 'Run this query to find duplicates:';
        RAISE WARNING 'SELECT photo_id, session_id, COUNT(*) FROM face_embeddings GROUP BY photo_id, session_id HAVING COUNT(*) > 1;';
END $$;

-- Step 8: Create new indexes for optimal performance
CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_id 
    ON face_embeddings(session_id);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_photo_id 
    ON face_embeddings(photo_id);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_session_photo 
    ON face_embeddings(session_id, photo_id);

-- Step 9: Create vector index for similarity search
-- Using IVFFlat index for large datasets (> 10k vectors)
-- lists parameter = sqrt(total_rows), adjust based on your data size
DO $$
DECLARE
    row_count INTEGER;
    lists_param INTEGER;
BEGIN
    SELECT COUNT(*) INTO row_count FROM face_embeddings;
    
    -- Calculate optimal lists parameter: sqrt(total_rows)
    lists_param := GREATEST(FLOOR(SQRT(row_count)), 10);
    
    RAISE NOTICE 'Creating vector index with lists=%', lists_param;
    
    -- Drop old index if exists
    DROP INDEX IF EXISTS idx_face_embeddings_vector;
    
    -- Create new IVFFlat index
    EXECUTE format('CREATE INDEX idx_face_embeddings_vector ON face_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = %s)', lists_param);
    
    RAISE NOTICE 'Vector index created successfully';
END $$;

-- Step 10: Update table comment
COMMENT ON TABLE face_embeddings IS 'Face embeddings for vector similarity search - v2.0 (isolated microservice)';

-- Step 11: Verify migration
DO $$
DECLARE
    final_count INTEGER;
    backup_count INTEGER;
    deleted_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO final_count FROM face_embeddings;
    SELECT COUNT(*) INTO backup_count FROM face_embeddings_backup;
    deleted_count := backup_count - final_count;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migration Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Original count: %', backup_count;
    RAISE NOTICE 'Final count: %', final_count;
    RAISE NOTICE 'Deleted: %', deleted_count;
    RAISE NOTICE '';
    RAISE NOTICE 'Backup table: face_embeddings_backup';
    RAISE NOTICE 'To rollback: See scripts/rollback_v2.sql';
    RAISE NOTICE '========================================';
END $$;

COMMIT;

-- Verification queries (run these after migration)
-- 
-- 1. Check schema:
-- \d face_embeddings
--
-- 2. Check indexes:
-- \di face_embeddings*
--
-- 3. Check constraints:
-- SELECT conname, contype FROM pg_constraint WHERE conrelid = 'face_embeddings'::regclass;
--
-- 4. Test vector search:
-- SELECT photo_id, 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) as similarity
-- FROM face_embeddings
-- WHERE session_id = 'your-session-uuid'
-- ORDER BY similarity DESC
-- LIMIT 10;
