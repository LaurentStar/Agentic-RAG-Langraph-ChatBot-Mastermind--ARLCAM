-- ============================================================
-- Token Version Migration for Session Invalidation
-- ============================================================
-- This migration adds the token_version column to the user account table.
-- This allows invalidating all tokens for a user without a sessions table.
--
-- Use cases:
-- - Password change
-- - Security breach suspected
-- - User requests "log out everywhere"
-- - Admin force logout
-- ============================================================

-- Add token_version column for session invalidation
ALTER TABLE gs_user_account_table_orm 
ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 1;

COMMENT ON COLUMN gs_user_account_table_orm.token_version IS 
'Increment to invalidate all active sessions/tokens for this user';
