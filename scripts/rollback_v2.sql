-- Facepass Microservice Isolation - Rollback Script v2.0
-- This script rolls back the migration_v2.sql changes
-- 
-- IMPORTANT: This script can only be run if face_embeddings_backup table exists!
-- The backup table is created automatically by migration_v2.sql
--
-- What this rollback does:
-- 1. Restores face_embeddings table from backup
-- 2. Recreates old indexes
-- 3. Removes new constraints and indexes
-- 4. Preserves the backup table for safety

BEGIN;

-- Step 1: Verify backup exists
DO $
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'face_embeddings_backup') THEN
        RAISE EXCEPTION 'Backup table face_embeddings_backup does not exist! Cannot rollback.';
    END IF;
    
    RAISE NOTICE 'Backup table found. Proceeding with rollback...';
END $;

-- Step 2: Get counts before rollback
DO $
DECLARE
    current_count INTEGER;
    backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO current_count FROM face_embeddings;
    SELECT COUNT(*) INTO backup_count FROM face_embeddings_backup;
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Rollback Pre-Check';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Current embeddings: %', current_count;
    RAISE NOTICE 'Backup embeddings: %', backup_count;
    RAISE NOTICE '';
END $;

-- Step 3: Drop new constraints
ALTER TABLE face_embeddings DROP CONSTRAINT IF EXISTS unique_photo_session;

-- Step 4: Drop new indexes
DROP INDEX IF EXISTS idx_face_embeddings_session_id;
DROP INDEX IF EXISTS idx_face_embeddings_photo_id;
DROP INDEX IF EXISTS idx_face_embeddings_session_photo;
DROP INDEX IF EXISTS idx_face_embeddings_vector;

-- Step 5: Drop NOT NULL constraints (restore nullable columns)
ALTER TABLE face_embeddings 
    ALTER COLUMN photo_id DROP NOT NULL,
    ALTER COLUMN session_id DROP NOT NULL,
    ALTER COLUMN embedding DROP NOT NULL,
    ALTER COLUMN confidence DROP NOT NULL;

-- Step 6: Re-add dropped columns (with NULL values initially)
ALTER TABLE face_embeddings 
    ADD COLUMN IF NOT EXISTS face_id UUID,
    ADD COLUMN IF NOT EXISTS event_id UUID;

-- Step 7: Truncate current table and restore from backup
TRUNCATE TABLE face_embeddings;

INSERT INTO face_embeddings 
SELECT * FROM face_embeddings_backup;

-- Step 8: Recreate old indexes
CREATE INDEX IF NOT EXISTS idx_face_embeddings_face_id 
    ON face_embeddings(face_id);

CREATE INDEX IF NOT EXISTS idx_face_embeddings_event_id 
    ON face_embeddings(event_id);

-- Recreate basic vector index (without IVFFlat optimization)
CREATE INDEX IF NOT EXISTS idx_face_embeddings_vector 
    ON face_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Step 9: Restore table comment
COMMENT ON TABLE face_embeddings IS 'Face embeddings for vector similarity search';

-- Step 10: Verify rollback
DO $
DECLARE
    final_count INTEGER;
    backup_count INTEGER;
    face_id_count INTEGER;
    event_id_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO final_count FROM face_embeddings;
    SELECT COUNT(*) INTO backup_count FROM face_embeddings_backup;
    SELECT COUNT(*) INTO face_id_count FROM face_embeddings WHERE face_id IS NOT NULL;
    SELECT COUNT(*) INTO event_id_count FROM face_embeddings WHERE event_id IS NOT NULL;
    
    RAISE NOTICE '';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Rollback Complete';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Restored count: %', final_count;
    RAISE NOTICE 'Backup count: %', backup_count;
    RAISE NOTICE 'Rows with face_id: %', face_id_count;
    RAISE NOTICE 'Rows with event_id: %', event_id_count;
    RAISE NOTICE '';
    
    IF final_count != backup_count THEN
        RAISE WARNING 'Row count mismatch! Expected %, got %', backup_count, final_count;
    ELSE
        RAISE NOTICE 'Row count matches backup ✓';
    END IF;
    
    RAISE NOTICE '';
    RAISE NOTICE 'Backup table preserved: face_embeddings_backup';
    RAISE NOTICE 'You can drop it manually if rollback is successful:';
    RAISE NOTICE 'DROP TABLE face_embeddings_backup;';
    RAISE NOTICE '========================================';
END $;

COMMIT;

-- Post-rollback verification queries
--
-- 1. Check schema (should have face_id and event_id columns):
-- \d face_embeddings
--
-- 2. Check indexes (should have old indexes):
-- \di face_embeddings*
--
-- 3. Check constraints (should NOT have unique_photo_session):
-- SELECT conname, contype FROM pg_constraint WHERE conrelid = 'face_embeddings'::regclass;
--
-- 4. Verify data integrity:
-- SELECT 
--     COUNT(*) as total,
--     COUNT(face_id) as with_face_id,
--     COUNT(event_id) as with_event_id,
--     COUNT(photo_id) as with_photo_id,
--     COUNT(session_id) as with_session_id
-- FROM face_embeddings;
