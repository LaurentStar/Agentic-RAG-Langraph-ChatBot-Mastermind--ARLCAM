import { z } from 'zod';
import { PlayerSchema } from './player';

// Game phase enum
export const GamePhaseSchema = z.enum([
  'phase1_actions',
  'lockout1',
  'phase2_reactions',
  'lockout2',
  'broadcast',
  'ending',
  'waiting',
]);

export type GamePhase = z.infer<typeof GamePhaseSchema>;

// Session status enum
export const SessionStatusSchema = z.enum(['waiting', 'active', 'paused', 'ended']);
export type SessionStatus = z.infer<typeof SessionStatusSchema>;

// Game session schema
export const SessionSchema = z.object({
  session_id: z.string(),
  session_name: z.string(),
  status: SessionStatusSchema,
  current_phase: GamePhaseSchema.nullable().optional(),
  player_count: z.number().min(0),
  max_players: z.number().min(2).max(6),
  players: z.array(PlayerSchema).optional(),
  created_at: z.string(),
  updated_at: z.string().optional(),
  host_player_id: z.string().optional(),
});

export type Session = z.infer<typeof SessionSchema>;

// Session list response (for pagination)
export const SessionListSchema = z.object({
  sessions: z.array(SessionSchema),
  nextPage: z.number().nullable(),
  total: z.number(),
});

export type SessionList = z.infer<typeof SessionListSchema>;

// Create session request
export const CreateSessionRequestSchema = z.object({
  session_name: z.string().min(1, 'Session name is required'),
  max_players: z.number().min(2).max(6).default(6),
});

export type CreateSessionRequest = z.infer<typeof CreateSessionRequestSchema>;

// Join session request
export const JoinSessionRequestSchema = z.object({
  session_id: z.string(),
  player_display_name: z.string().optional(),
});

export type JoinSessionRequest = z.infer<typeof JoinSessionRequestSchema>;
