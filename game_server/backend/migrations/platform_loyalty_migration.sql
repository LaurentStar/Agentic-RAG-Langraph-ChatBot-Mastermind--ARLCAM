-- =============================================
-- Platform Loyalty Migration
-- =============================================
-- Adds platform loyalty tracking to player_table_orm
-- Run this migration BEFORE deploying the new code
-- =============================================

-- Step 1: Add new columns
ALTER TABLE player_table_orm 
ADD COLUMN IF NOT EXISTS social_media_platforms social_media_platform_enum[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS preferred_social_media_platform social_media_platform_enum;

-- Step 2: Migrate existing data from old column to new array column
-- This converts the single social_media_platform value to an array
UPDATE player_table_orm 
SET 
    social_media_platforms = ARRAY[social_media_platform],
    preferred_social_media_platform = social_media_platform
WHERE social_media_platform IS NOT NULL 
  AND (social_media_platforms IS NULL OR social_media_platforms = '{}');

-- Step 3: Verify migration (run this to check)
-- SELECT display_name, social_media_platform, social_media_platforms, preferred_social_media_platform 
-- FROM player_table_orm;

-- Step 4: Drop old column (OPTIONAL - run only after verification)
-- ALTER TABLE player_table_orm DROP COLUMN social_media_platform;

-- =============================================
-- Rollback (if needed)
-- =============================================
-- ALTER TABLE player_table_orm DROP COLUMN IF EXISTS social_media_platforms;
-- ALTER TABLE player_table_orm DROP COLUMN IF EXISTS preferred_social_media_platform;

