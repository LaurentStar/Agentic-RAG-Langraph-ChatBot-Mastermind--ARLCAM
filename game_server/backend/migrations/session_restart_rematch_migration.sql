-- =============================================
-- Session Restart, Rematch, and Phase Renaming Migration
-- =============================================
-- This migration:
-- 1. Renames phase duration columns for clarity
-- 2. Adds new columns for ending phase, rematch tracking, and winners
-- 3. Adds ENDING value to game_phase_enum
-- =============================================
-- IMPORTANT: PostgreSQL enum labels use the Python enum MEMBER NAMES (uppercase)
-- NOT the .value attribute (lowercase). Example:
--   Python: GamePhase.PHASE1_ACTIONS = 'phase1_actions'
--   PostgreSQL stores: 'PHASE1_ACTIONS' (the member name)
--   API returns: 'phase1_actions' (the .value)
-- =============================================

-- =============================================
-- Step 1: Rename phase duration columns
-- =============================================
ALTER TABLE game_session_table_orm 
RENAME COLUMN phase1_duration TO phase1_action_duration;

ALTER TABLE game_session_table_orm 
RENAME COLUMN lockout1_duration TO phase2_lockout_duration;

ALTER TABLE game_session_table_orm 
RENAME COLUMN phase2_duration TO phase3_reaction_duration;

ALTER TABLE game_session_table_orm 
RENAME COLUMN lockout2_duration TO phase4_lockout_duration;

ALTER TABLE game_session_table_orm 
RENAME COLUMN broadcast_duration TO phase5_broadcast_duration;

-- =============================================
-- Step 2: Add new columns
-- =============================================
ALTER TABLE game_session_table_orm 
ADD COLUMN IF NOT EXISTS phase6_ending_duration INTEGER DEFAULT 5;

ALTER TABLE game_session_table_orm 
ADD COLUMN IF NOT EXISTS rematch_count INTEGER DEFAULT 0;

ALTER TABLE game_session_table_orm 
ADD COLUMN IF NOT EXISTS winners TEXT[] DEFAULT '{}';

-- =============================================
-- Step 3: Add ENDING to game_phase_enum (UPPERCASE)
-- =============================================
ALTER TYPE game_phase_enum ADD VALUE IF NOT EXISTS 'ENDING';

-- =============================================
-- Verification Queries
-- =============================================
-- Check enum values (should all be UPPERCASE):
-- SELECT enumlabel FROM pg_enum 
-- WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'game_phase_enum');

-- =============================================
-- Rollback (if needed)
-- =============================================
-- ALTER TABLE game_session_table_orm RENAME COLUMN phase1_action_duration TO phase1_duration;
-- ALTER TABLE game_session_table_orm RENAME COLUMN phase2_lockout_duration TO lockout1_duration;
-- ALTER TABLE game_session_table_orm RENAME COLUMN phase3_reaction_duration TO phase2_duration;
-- ALTER TABLE game_session_table_orm RENAME COLUMN phase4_lockout_duration TO lockout2_duration;
-- ALTER TABLE game_session_table_orm RENAME COLUMN phase5_broadcast_duration TO broadcast_duration;
-- ALTER TABLE game_session_table_orm DROP COLUMN IF EXISTS phase6_ending_duration;
-- ALTER TABLE game_session_table_orm DROP COLUMN IF EXISTS rematch_count;
-- ALTER TABLE game_session_table_orm DROP COLUMN IF EXISTS winners;

