import { z } from 'zod';

// Player type enum
export const PlayerTypeSchema = z.enum(['human', 'llm_agent', 'admin']);
export type PlayerType = z.infer<typeof PlayerTypeSchema>;

// Social media platform enum
export const SocialMediaPlatformSchema = z.enum(['discord', 'slack', 'google', 'web']);
export type SocialMediaPlatform = z.infer<typeof SocialMediaPlatformSchema>;

// Player schema (runtime validation)
export const PlayerSchema = z.object({
  display_name: z.string(),
  coins: z.number().min(0),
  is_alive: z.boolean(),
  player_type: PlayerTypeSchema,
  social_media_platforms: z.array(z.string()),
  session_id: z.string().nullable(),
  avatar_url: z.string().nullable().optional(),
  created_at: z.string().optional(),
});

// Infer TypeScript type from schema (DRY - no duplication!)
export type Player = z.infer<typeof PlayerSchema>;

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
