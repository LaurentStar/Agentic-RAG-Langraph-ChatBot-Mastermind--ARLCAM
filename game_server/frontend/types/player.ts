import { z } from 'zod';

// Player type enum
export const PlayerTypeSchema = z.enum(['human', 'llm_agent', 'admin']);
export type PlayerType = z.infer<typeof PlayerTypeSchema>;

// Social media platform enum
export const SocialMediaPlatformSchema = z.enum(['discord', 'slack', 'google', 'web']);
export type SocialMediaPlatform = z.infer<typeof SocialMediaPlatformSchema>;

// User account schema (identity/auth)
export const UserAccountSchema = z.object({
  user_id: z.string(),
  user_name: z.string(),
  display_name: z.string(),
  player_type: PlayerTypeSchema,
  social_media_platforms: z.array(z.string()),
  preferred_social_media_platform: z.string().nullable().optional(),
  social_media_platform_display_name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  email_verified: z.boolean().optional(),
  account_status: z.string().optional(),
  created_at: z.string().optional(),
});

export type UserAccount = z.infer<typeof UserAccountSchema>;

// Player schema (combines user account + game state for backwards compatibility)
export const PlayerSchema = z.object({
  user_id: z.string().optional(),
  user_name: z.string().optional(),
  display_name: z.string(),
  coins: z.number().min(0).nullable(),
  is_alive: z.boolean().nullable(),
  player_type: PlayerTypeSchema,
  social_media_platforms: z.array(z.string()),
  session_id: z.string().nullable(),
  avatar_url: z.string().nullable().optional(),
  created_at: z.string().optional(),
});

// Infer TypeScript type from schema (DRY - no duplication!)
export type Player = z.infer<typeof PlayerSchema>;

// Player game state schema (per-session transient state)
export const PlayerGameStateSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  session_id: z.string().nullable(),
  coins: z.number().min(0),
  is_alive: z.boolean(),
  card_count: z.number().min(0),
  joined_at: z.string().optional(),
});

export type PlayerGameState = z.infer<typeof PlayerGameStateSchema>;

// Player list response
export const PlayerListSchema = z.object({
  players: z.array(PlayerSchema),
  total: z.number(),
});

export type PlayerList = z.infer<typeof PlayerListSchema>;

// Player update request
export const PlayerUpdateSchema = z.object({
  display_name: z.string().optional(),
  avatar_url: z.string().nullable().optional(),
});

export type PlayerUpdate = z.infer<typeof PlayerUpdateSchema>;
