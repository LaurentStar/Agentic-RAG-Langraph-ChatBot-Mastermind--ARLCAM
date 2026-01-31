-- ============================================================
-- Three-Tier Account Architecture Migration
-- ============================================================
-- This migration creates the three-tier account architecture:
--   1. user_account - Identity, auth, account status
--   2. player_profile - Persistent stats, preferences
--   3. player_game_state - Per-session game state
--
-- Run this migration in a transaction with backups!
-- ============================================================

BEGIN;

-- ============================================================
-- PHASE 1: Create new tables
-- ============================================================

-- 1.1 Create user_account_table_orm table
CREATE TABLE IF NOT EXISTS user_account_table_orm (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_name VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255),
    account_status VARCHAR(20) NOT NULL DEFAULT 'active',
    player_type player_type_enum DEFAULT 'HUMAN',
    game_privileges game_privilege_enum[] DEFAULT '{}',
    social_media_platforms social_media_platform_enum[] DEFAULT '{}',
    preferred_social_media_platform social_media_platform_enum,
    social_media_platform_display_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_account_user_name ON user_account_table_orm(user_name);
CREATE INDEX IF NOT EXISTS idx_user_account_display_name ON user_account_table_orm(display_name);
CREATE INDEX IF NOT EXISTS idx_user_account_email ON user_account_table_orm(email);
CREATE INDEX IF NOT EXISTS idx_user_account_status ON user_account_table_orm(account_status);

-- 1.2 Create player_profile_table_orm table
CREATE TABLE IF NOT EXISTS player_profile_table_orm (
    user_id UUID PRIMARY KEY REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    avatar_url VARCHAR(500),
    bio TEXT,
    games_played INTEGER DEFAULT 0,
    games_won INTEGER DEFAULT 0,
    games_lost INTEGER DEFAULT 0,
    games_abandoned INTEGER DEFAULT 0,
    rank VARCHAR(50),
    elo INTEGER DEFAULT 1000,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    achievements JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 1.3 Create player_game_state_table_orm table
CREATE TABLE IF NOT EXISTS player_game_state_table_orm (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    session_id VARCHAR REFERENCES game_session_table_orm(session_id) ON DELETE SET NULL,
    card_types card_type_enum[] DEFAULT '{}',
    player_statuses player_status_enum[] DEFAULT '{}',
    coins INTEGER DEFAULT 2,
    debt INTEGER DEFAULT 0,
    target_display_name VARCHAR(100),
    to_be_initiated to_be_initiated_enum[] DEFAULT '{}',
    joined_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_player_game_state_user_id ON player_game_state_table_orm(user_id);
CREATE INDEX IF NOT EXISTS idx_player_game_state_session_id ON player_game_state_table_orm(session_id);

-- 1.4 Create new upgrade_details table (linked to game_state)
CREATE TABLE IF NOT EXISTS to_be_initiated_upgrade_details_table_orm (
    game_state_id UUID PRIMARY KEY REFERENCES player_game_state_table_orm(id) ON DELETE CASCADE,
    assassination_priority card_type_enum,
    kleptomania_steal BOOLEAN DEFAULT FALSE,
    trigger_identity_crisis BOOLEAN DEFAULT FALSE,
    identify_as_tax_liability BOOLEAN DEFAULT FALSE,
    tax_debt INTEGER DEFAULT 0
);

-- ============================================================
-- PHASE 2: Migrate data from player_table_orm to new tables
-- ============================================================

-- 2.1 Migrate to user_account (identity + auth fields)
INSERT INTO user_account_table_orm (
    user_id,
    user_name,
    display_name,
    password_hash,
    player_type,
    game_privileges,
    social_media_platforms,
    preferred_social_media_platform,
    social_media_platform_display_name,
    created_at
)
SELECT 
    gen_random_uuid(),
    -- user_name = lowercase display_name with spaces replaced
    LOWER(REPLACE(display_name, ' ', '_')),
    display_name,
    password_hash,
    player_type,
    game_privileges,
    social_media_platforms,
    preferred_social_media_platform,
    social_media_platform_display_name,
    NOW()
FROM player_table_orm
ON CONFLICT (display_name) DO NOTHING;

-- 2.2 Create player_profile for each user
INSERT INTO player_profile_table_orm (user_id)
SELECT user_id FROM user_account_table_orm
ON CONFLICT (user_id) DO NOTHING;

-- 2.3 Migrate game state (for players currently in a session)
INSERT INTO player_game_state_table_orm (
    id,
    user_id,
    session_id,
    card_types,
    player_statuses,
    coins,
    debt,
    target_display_name,
    to_be_initiated,
    joined_at
)
SELECT 
    gen_random_uuid(),
    ua.user_id,
    p.session_id,
    p.card_types,
    p.player_statuses,
    p.coins,
    p.debt,
    p.target_display_name,
    p.to_be_initiated,
    NOW()
FROM player_table_orm p
JOIN user_account_table_orm ua ON ua.display_name = p.display_name
WHERE p.session_id IS NOT NULL;

-- ============================================================
-- PHASE 3: Create new child tables with user_id FK
-- ============================================================

-- 3.1 Update oauth_identity to use user_id
ALTER TABLE oauth_identity_table_orm 
    ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE oauth_identity_table_orm oi
SET user_id = ua.user_id
FROM user_account_table_orm ua
WHERE ua.display_name = oi.player_display_name;

-- 3.2 Update account_flag to use user_id
ALTER TABLE account_flag_table_orm 
    ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE account_flag_table_orm af
SET user_id = ua.user_id
FROM user_account_table_orm ua
WHERE ua.display_name = af.player_display_name;

-- 3.3 Update account_link_request to use user_id
ALTER TABLE account_link_request_table_orm 
    ADD COLUMN IF NOT EXISTS user_id UUID;

UPDATE account_link_request_table_orm alr
SET user_id = ua.user_id
FROM user_account_table_orm ua
WHERE ua.display_name = alr.player_display_name;

-- 3.4 Create new agent_profile_table_orm table with user_id
CREATE TABLE IF NOT EXISTS agent_profile_table_orm (
    user_id UUID PRIMARY KEY REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    personality_type VARCHAR(50) DEFAULT 'balanced',
    aggression FLOAT DEFAULT 0.5,
    bluff_confidence FLOAT DEFAULT 0.5,
    challenge_tendency FLOAT DEFAULT 0.5,
    block_tendency FLOAT DEFAULT 0.5,
    risk_tolerance FLOAT DEFAULT 0.5,
    llm_reliance FLOAT DEFAULT 0.5,
    model_name VARCHAR(100) DEFAULT 'gpt-4',
    temperature FLOAT DEFAULT 0.7
);

-- Migrate agent profiles from old table
INSERT INTO agent_profile_table_orm (
    user_id, personality_type, aggression, bluff_confidence, 
    challenge_tendency, block_tendency, risk_tolerance, llm_reliance,
    model_name, temperature
)
SELECT 
    ua.user_id,
    ap.personality_type,
    ap.aggression,
    ap.bluff_confidence,
    ap.challenge_tendency,
    ap.block_tendency,
    ap.risk_tolerance,
    ap.llm_reliance,
    ap.model_name,
    ap.temperature
FROM agent_profile_old_table_orm ap
JOIN user_account_table_orm ua ON ua.display_name = ap.display_name
ON CONFLICT (user_id) DO NOTHING;

-- 3.5 Create new reaction_table_orm with user_id
CREATE TABLE IF NOT EXISTS reaction_table_orm (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR REFERENCES game_session_table_orm(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    reactor_user_id UUID REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    target_action to_be_initiated_enum,
    reaction_type reaction_type_enum,
    block_with_role VARCHAR(50),
    is_locked BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reaction_session_id ON reaction_table_orm(session_id);
CREATE INDEX IF NOT EXISTS idx_reaction_reactor ON reaction_table_orm(reactor_user_id);
CREATE INDEX IF NOT EXISTS idx_reaction_actor ON reaction_table_orm(actor_user_id);

-- Migrate reactions from old table
INSERT INTO reaction_table_orm (
    session_id, turn_number, reactor_user_id, actor_user_id,
    target_action, reaction_type, block_with_role, is_locked, is_resolved, created_at
)
SELECT 
    r.session_id,
    r.turn_number,
    reactor.user_id,
    actor.user_id,
    r.target_action,
    r.reaction_type,
    r.block_with_role,
    r.is_locked,
    r.is_resolved,
    r.created_at
FROM reaction_old_table_orm r
JOIN user_account_table_orm reactor ON reactor.display_name = r.reactor_display_name
JOIN user_account_table_orm actor ON actor.display_name = r.actor_display_name;

-- 3.6 Create new turn_result_table_orm table
CREATE TABLE IF NOT EXISTS turn_result_table_orm (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR REFERENCES game_session_table_orm(session_id) ON DELETE CASCADE,
    turn_number INTEGER NOT NULL,
    results_json JSONB DEFAULT '{}',
    summary VARCHAR(1000) DEFAULT '',
    players_eliminated VARCHAR(100)[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_turn_result_session ON turn_result_table_orm(session_id);

-- Migrate turn results from old table
INSERT INTO turn_result_table_orm (
    session_id, turn_number, results_json, summary, players_eliminated, created_at
)
SELECT 
    session_id, turn_number, results_json, summary, players_eliminated, created_at
FROM turn_result_old_table_orm;

-- 3.7 Create new chat_message_table_orm table with user_id
CREATE TABLE IF NOT EXISTS chat_message_table_orm (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL REFERENCES game_session_table_orm(session_id) ON DELETE CASCADE,
    sender_user_id UUID NOT NULL REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE,
    sender_display_name VARCHAR(100) NOT NULL,
    sender_platform social_media_platform_enum NOT NULL,
    content VARCHAR(2000) NOT NULL,
    is_broadcast BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message_table_orm(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_sender ON chat_message_table_orm(sender_user_id);

-- Migrate chat messages from old table
INSERT INTO chat_message_table_orm (
    session_id, sender_user_id, sender_display_name, sender_platform, content, created_at
)
SELECT 
    cm.session_id,
    ua.user_id,
    cm.sender_display_name,
    cm.sender_platform,
    cm.content,
    cm.created_at
FROM chat_message_old_table_orm cm
JOIN user_account_table_orm ua ON ua.display_name = cm.sender_display_name;

-- ============================================================
-- PHASE 4: Add FK constraints and indexes after data migration
-- ============================================================

-- Add FK constraints to updated tables
ALTER TABLE oauth_identity_table_orm
    ADD CONSTRAINT fk_oauth_identity_user 
    FOREIGN KEY (user_id) REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE;

ALTER TABLE account_flag_table_orm
    ADD CONSTRAINT fk_account_flag_user 
    FOREIGN KEY (user_id) REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE;

ALTER TABLE account_link_request_table_orm
    ADD CONSTRAINT fk_account_link_request_user 
    FOREIGN KEY (user_id) REFERENCES user_account_table_orm(user_id) ON DELETE CASCADE;

-- Create indexes on new FK columns
CREATE INDEX IF NOT EXISTS idx_oauth_identity_user_id ON oauth_identity_table_orm(user_id);
CREATE INDEX IF NOT EXISTS idx_account_flag_user_id ON account_flag_table_orm(user_id);
CREATE INDEX IF NOT EXISTS idx_account_link_request_user_id ON account_link_request_table_orm(user_id);

-- ============================================================
-- PHASE 5: Cleanup (OPTIONAL - run after verification)
-- ============================================================
-- Uncomment these after verifying data migration is complete
-- 
-- -- Drop old columns from updated tables
-- ALTER TABLE oauth_identity_table_orm DROP COLUMN IF EXISTS player_display_name;
-- ALTER TABLE account_flag_table_orm DROP COLUMN IF EXISTS player_display_name;
-- ALTER TABLE account_link_request_table_orm DROP COLUMN IF EXISTS player_display_name;
-- 
-- -- Drop old tables
-- DROP TABLE IF EXISTS to_be_initiated_upgrade_details_table_orm;
-- DROP TABLE IF EXISTS agent_profile_table_orm;
-- DROP TABLE IF EXISTS reaction_table_orm;
-- DROP TABLE IF EXISTS turn_result_table_orm;
-- DROP TABLE IF EXISTS chat_message_table_orm;
-- DROP TABLE IF EXISTS player_table_orm;

COMMIT;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================
-- Run these after migration to verify data integrity:
--
-- SELECT COUNT(*) as user_accounts FROM user_account_table_orm;
-- SELECT COUNT(*) as player_profiles FROM player_profile_table_orm;
-- SELECT COUNT(*) as game_states FROM player_game_state_table_orm;
-- SELECT COUNT(*) as original_players FROM player_table_orm;
--
-- -- Check for any orphaned records
-- SELECT COUNT(*) as oauth_without_user FROM oauth_identity_table_orm WHERE user_id IS NULL;
-- SELECT COUNT(*) as flags_without_user FROM account_flag_table_orm WHERE user_id IS NULL;
